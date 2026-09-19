"""Repeat one registered target with a larger output budget and exact initial input.

Prior worker tool actions are replayed without model generation. The target's
first model messages and ordered tool schemas must match the primary run.
No source final answer or SQL interpretation is placed in model input.
"""
import argparse
import asyncio
from datetime import timedelta
import importlib.metadata
import json
import os
from pathlib import Path
import sys

from .local_smoke import sha256_file as sha
from .native_tool_agent import NativeTransformersModel
from .vakra_mcp_audit import decode_result
from .vakra_native import run_episode


def stable(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=True)


class InitialInputGuard:
    def __init__(self, model, messages, tools):
        if len(messages) != 2 or [m['role'] for m in messages] != ['system', 'user']:
            raise ValueError('Expected a fresh two-message primary target')
        self.model, self.messages, self.tools = model, stable(messages), stable(tools)
        self.checked = False
        self.failure = None

    def generate_tools(self, messages, tools, max_new_tokens):
        if not self.checked:
            if stable(messages) != self.messages or stable(tools) != self.tools:
                self.failure = 'Target initial messages or ordered schemas differ from primary run'
                raise ValueError(self.failure)
            self.checked = True
        return self.model.generate_tools(messages, tools, max_new_tokens)


class InitialPeekGuard:
    def __init__(self, session, uuid, peek):
        self.session, self.uuid, self.peek = session, uuid, stable(peek)
        self.checked = False

    async def call_tool(self, name, arguments):
        if not self.checked and (name != 'get_data' or arguments != {'tool_universe_id': self.uuid}):
            raise ValueError('Unexpected first target initialization request')
        result = await self.session.call_tool(name, arguments)
        if not self.checked:
            if stable(decode_result(result)) != self.peek:
                raise ValueError('Target initial preview differs from primary run')
            self.checked = True
        return result

    async def list_tools(self):
        return await self.session.list_tools()


def calls(raw):
    for event in raw.get('trace', []):
        for record in event.get('calls', [event]):
            if 'tool_call' in record:
                yield record


async def run(args):
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client
    primary = json.loads((args.primary_worker / 'manifest.json').read_bytes())
    prep = json.loads((args.prepared / 'preparation_manifest.json').read_bytes())
    assert primary['preparation_sha256'] == sha(args.prepared / 'preparation_manifest.json')
    assert primary['agent_prompt_source_sha256'] == sha(args.agent_source)
    assert primary['max_new_tokens'] == 512 and args.max_new_tokens == 8192
    assert primary['max_steps'] == primary['max_tool_calls'] == 20
    assert primary['max_input_tokens'] == 32768 and primary['call_policy'] == 'sequential'
    assert primary['template_profile'] == 'standard'
    for name, digest in primary['source_sha256'].items():
        assert sha(Path(__file__).parent / name) == digest, name
    for name, version in primary['packages'].items():
        assert importlib.metadata.version(name) == version, name
    for name, digest in primary['model_files_sha256'].items():
        assert sha(args.model_path / name) == digest, name
    for name, digest in prep['runtime_files'].items():
        assert sha(args.prepared / 'runtime' / name) == digest, name
    database = args.prepared / (prep['domain'] + '.sqlite')
    assert sha(database) == prep['database_sha256']
    assert sha(args.prepared / 'queries.json') == prep['prepared_queries_sha256']
    target_path = args.primary_worker / f'case-{args.task_index:03d}.json'
    target = json.loads(target_path.read_bytes())
    prior_paths = [args.primary_worker / f'case-{i:03d}.json' for i in range(args.task_index)]
    queries = json.loads((args.prepared / 'queries.json').read_bytes())
    query = next(q for q in queries if q['uuid'] == target['uuid'])
    assert target['uuid'] == primary['selected_task_ids'][args.task_index]
    assert (prep['domain'], args.task_index, target['uuid']) in {
        ('cookbook', 1, 'ec134bf7bda5-0e705a585aa7'),
        ('ice_hockey_draft', 0, 'd0d7be63ebc2-778e84fced89')}
    args.output.mkdir(parents=True, exist_ok=False)
    metadata = {'purpose': __doc__, 'primary_manifest_sha256': sha(args.primary_worker / 'manifest.json'),
                'primary_target_sha256': sha(target_path),
                'primary_prefix_sha256': {p.name: sha(p) for p in prior_paths},
                'new_max_new_tokens': 8192, 'primary_configuration': primary,
                'target_uuid': target['uuid'], 'task_index': args.task_index,
                'script_sha256': sha(Path(__file__)), 'status': 'initializing'}
    with (args.output / 'initialization.json').open('x', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    model = NativeTransformersModel(args.model_path, max_input_tokens=32768,
                                   device_profile=primary['device_profile'], template_profile='standard')
    metadata['placement'] = dict(model.runtime_placement)
    metadata['placement']['hf_device_map'] = {
        k: str(v) for k, v in model.runtime_placement['hf_device_map'].items()}
    first = target.get('trace', [{}])[0]
    guard = InitialInputGuard(model, first['input'], target['tools'])
    params = StdioServerParameters(command=sys.executable,
        args=['-X', 'utf8', '-m', 'autolab.vakra_stdio', '--runtime', str(args.prepared / 'runtime'),
              '--database', str(database), '--domain', prep['domain']],
        cwd=str(Path(__file__).resolve().parent.parent),
        env={'PYTHON_DOTENV_DISABLED':'1', 'PYTHONUTF8':'1', 'PYTHONPATH':os.environ.get('PYTHONPATH','')})
    try:
        with (args.output / 'server.stderr.log').open('x', encoding='utf-8') as log:
            async with stdio_client(params, errlog=log) as (read, write):
                async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=60)) as session:
                    await session.initialize()
                    startup = json.loads((args.primary_worker / 'startup.json').read_bytes())
                    warm = decode_result(await session.call_tool('get_data', {'tool_universe_id': startup['uuid']}))
                    assert stable(warm) == stable(startup['peek']), 'Warmup mismatch'
                    for path in prior_paths:
                        previous = json.loads(path.read_bytes())
                        peek = decode_result(await session.call_tool('get_data', {'tool_universe_id': previous['uuid']}))
                        assert stable(peek) == stable(previous['initial_peek']), 'Prefix initial mismatch'
                        for record in calls(previous):
                            call = record['tool_call']
                            result = (await session.call_tool(call['name'], call['arguments'])).model_dump(mode='json')
                            assert all(stable(result[k]) == stable(record['tool_result'][k]) for k in ('content','isError')), 'Prefix result mismatch'
                    guarded_session = InitialPeekGuard(session, target['uuid'], target['initial_peek'])
                    episode = await run_episode(guard, guarded_session, query, args.agent_source, 20, 8192,
                                                primary['instruction_condition'], 'sequential', 20)
                    with (args.output / 'case-000.json').open('x', encoding='utf-8') as f:
                        json.dump(episode, f, ensure_ascii=False, indent=2)
                    metadata.update(status='complete' if guard.checked else 'pairing_failed',
                                    exact_initial_input_verified=guard.checked, pairing_error=guard.failure,
                                    exact_initial_peek_verified=guarded_session.checked,
                                    termination=episode['termination'])
    except Exception as exc:
        metadata.update(status='failed', error_type=type(exc).__name__, error=str(exc),
                        exact_initial_input_verified=guard.checked, pairing_error=guard.failure)
        raise
    finally:
        metadata['database_unchanged'] = sha(database) == prep['database_sha256']
        with (args.output / 'manifest.json').open('x', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(json.dumps({k: metadata[k] for k in ('status','exact_initial_input_verified','termination')}))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('primary-worker','prepared','agent-source','model-path','output'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--task-index', type=int, required=True)
    p.add_argument('--max-new-tokens', type=int, default=8192)
    a = p.parse_args()
    asyncio.run(run(a))


if __name__ == '__main__':
    main()
