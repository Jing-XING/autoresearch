"""Exercise the new adapter on real MCP with fixed recorded model text.

This is a CPU regression fixture, not a model continuation or answer evaluation.
"""
import asyncio
from collections import Counter
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autolab.native_tool_agent import NativeModelReply, parse_calls
from autolab.vakra_native import run_episode
from autolab.vakra_mcp_audit import decode_result


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RecordedModel:
    def __init__(self, texts):
        self.texts = iter(texts)

    def generate_tools(self, *unused):
        text = next(self.texts)
        return NativeModelReply(text, 0, 0, 0.0, text, text, [], "")


async def main():
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client
    diagnostic = ROOT / 'research/evidence/vakra_crossdomain_v1_rejected_batch_audit.json'
    original_root = ROOT / 'results/remote/vakra-crossdomain-v1/runs/vakra-crossdomain-v1'
    cases = json.loads(diagnostic.read_bytes())['rows']
    output = ROOT / 'research/evidence/vakra_sequential_adapter_preflight.json'
    assert not output.exists()
    rows = []
    with output.with_suffix('.stderr.log').open('x', encoding='utf-8') as log:
        for domain in sorted({c['source'].split('/')[0] for c in cases}):
            prep = ROOT / f'results/vakra-{domain}-replication-v1'
            manifest = json.loads((prep / 'preparation_manifest.json').read_bytes())
            database = prep / f'{domain}.sqlite'
            assert sha(database) == manifest['database_sha256']
            for name, digest in manifest['runtime_files'].items():
                assert sha(prep / 'runtime' / name) == digest
            queries = json.loads((prep / 'queries.json').read_bytes())
            params = StdioServerParameters(command=sys.executable,
                args=['-X', 'utf8', '-m', 'autolab.vakra_stdio', '--runtime', str(prep / 'runtime'),
                      '--database', str(database), '--domain', domain], cwd=str(ROOT),
                env={'PYTHON_DOTENV_DISABLED': '1', 'PYTHONUTF8': '1', 'PYTHONPATH': str(ROOT)})
            async with stdio_client(params, errlog=log) as (read, write):
                async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=60)) as session:
                    await session.initialize()
                    for case in cases:
                        if case['source'].split('/')[0] != domain:
                            continue
                        source = original_root / case['source']
                        assert sha(source) == case['source_sha256']
                        raw = json.loads(source.read_bytes())
                        warm = next(q['uuid'] for q in queries if q['uuid'] != raw['uuid'])
                        decode_result(await session.call_tool('get_data', {'tool_universe_id': warm}))
                        stop = case['rejected_step']
                        fixture = RecordedModel([e['reply']['text'] for e in raw['trace'][:stop + 1]]
                                                + ['SCRIPTED_PREFLIGHT_END'])
                        result = await run_episode(fixture, session, raw['query'],
                            ROOT / 'results/third_party/vakra/agents/agent_interface.py',
                            30, 512, raw['instruction_condition'], 'sequential', 20)
                        assert result['initial_peek'] == raw['initial_peek']
                        for old, new in zip(raw['trace'][:stop], result['trace'][:stop]):
                            if 'tool_call' in old:
                                assert len(new['calls']) == 1
                                assert new['calls'][0]['tool_call'] == old['tool_call']
                                assert new['calls'][0]['tool_result']['content'] == old['tool_result']['content']
                                assert new['calls'][0]['tool_result']['isError'] == old['tool_result']['isError']
                        event = result['trace'][stop]
                        executed = event.get('calls', [])
                        for actual, expected in zip(executed, case['calls']):
                            assert actual['tool_call'] == expected['call']
                            assert actual['tool_result']['content'] == expected['mcp_result']['content']
                            assert actual['tool_result']['isError'] == expected['mcp_result']['isError']
                        status = ('executed' if executed else 'protocol_rejection' if 'protocol_error' in event
                                  else 'budget_rejection' if 'tool_budget_rejection' in event else 'unexpected')
                        assert status != 'unexpected'
                        if status == 'executed':
                            assert len(executed) == len(case['calls'])
                            assert result['final_answer'] == 'SCRIPTED_PREFLIGHT_END'
                        rows.append({'source': case['source'], 'source_sha256': sha(source),
                            'rejected_step': stop, 'fixture_status': status,
                            'requested_calls': len(parse_calls(raw['trace'][stop]['reply']['text'])),
                            'executed_calls': len(executed), 'event': event,
                            'termination': result['termination']})
            assert sha(database) == manifest['database_sha256']
    report = {'purpose': __doc__, 'episodes': len(rows),
        'fixture_status': dict(Counter(r['fixture_status'] for r in rows)),
        'executed_batch_calls': sum(r['executed_calls'] for r in rows),
        'source_sha256': sha(Path(__file__)), 'adapter_sha256': sha(ROOT / 'autolab/vakra_native.py'),
        'diagnostic_sha256': sha(diagnostic), 'rows': rows,
        'limits': 'Recorded assistant text, zero token accounting, 30 fixture steps; not a neural run. Prefix tool results and executed batch responses must match prior CPU replay exactly. Dynamic schema order is not a model-equivalence claim.'}
    with output.open('x', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps({k: report[k] for k in ('episodes', 'fixture_status', 'executed_batch_calls')}))


if __name__ == '__main__':
    asyncio.run(main())
