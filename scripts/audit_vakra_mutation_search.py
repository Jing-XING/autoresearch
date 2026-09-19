"""Replay bounded development mutations through the unchanged real MCP server.

Every witness preserves a target episode's complete recorded tool observation.
Search exhaustion means unknown, never a positive sufficiency certificate.
"""
import asyncio
from collections import Counter
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autolab.relational_mutations import answer, apply
from autolab.vakra_mcp_audit import decode_result


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=True).encode()


def calls(raw):
    for event in raw['trace']:
        for record in event.get('calls', [event]):
            if 'tool_call' in record:
                yield record


async def replay(prepared, database, raw, prior, warm, log):
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client
    params = StdioServerParameters(command=sys.executable,
        args=['-X', 'utf8', '-m', 'autolab.vakra_stdio', '--runtime', str(prepared / 'runtime'),
              '--database', str(database), '--domain', 'world'], cwd=str(ROOT),
        env={'PYTHON_DOTENV_DISABLED': '1', 'PYTHONUTF8': '1', 'PYTHONPATH': str(ROOT)})
    previous_differences = 0
    async with stdio_client(params, errlog=log) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=60)) as session:
            await session.initialize()
            await session.call_tool('get_data', {'tool_universe_id': warm})
            for previous in prior:
                peek = decode_result(await session.call_tool('get_data', {'tool_universe_id': previous['uuid']}))
                previous_differences += stable(peek) != stable(previous['initial_peek'])
                for event in calls(previous):
                    call = event['tool_call']
                    result = (await session.call_tool(call['name'], call['arguments'])).model_dump(mode='json')
                    previous_differences += any(result[k] != event['tool_result'][k] for k in ('content', 'isError'))
            peek = decode_result(await session.call_tool('get_data', {'tool_universe_id': raw['uuid']}))
            metadata = {'previous_independent_episode_differences': previous_differences}
            if stable(peek) != stable(raw['initial_peek']):
                return {**metadata, 'preserved': False, 'first_difference': 'initial_peek'}
            schemas = [{'type': 'function', 'function': {'name': t.name,
                'description': t.description or '', 'parameters': t.inputSchema}}
                for t in (await session.list_tools()).tools]
            if stable(schemas) != stable(raw['tools']):
                return {**metadata, 'preserved': False, 'first_difference': 'ordered_tool_schemas'}
            observations = []
            for index, event in enumerate(calls(raw)):
                call = event['tool_call']
                result = (await session.call_tool(call['name'], call['arguments'])).model_dump(mode='json')
                if any(result[k] != event['tool_result'][k] for k in ('content', 'isError')):
                    return {**metadata, 'preserved': False, 'first_difference': 'tool_response',
                            'call_index': index, 'call': call}
                observations.append({'call': call, 'content': result['content'], 'isError': result['isError']})
    digest = hashlib.sha256(stable({'initial_peek': peek, 'tools': schemas, 'events': observations})).hexdigest()
    return {**metadata, 'preserved': True, 'calls_checked': len(observations), 'observation_sha256': digest}


async def main(candidate_path=None, output=None, summary_path=None):
    candidate_path = candidate_path or ROOT / 'research/evidence/vakra_world_mutation_candidates_v1.json'
    candidates = json.loads(candidate_path.read_bytes())
    assert candidates['mutation_source_sha256'] == sha(ROOT / 'autolab/relational_mutations.py')
    prepared = ROOT / 'results/vakra-world-runtime-v3'
    prep = json.loads((prepared / 'preparation_manifest.json').read_bytes())
    database = prepared / 'world.sqlite'
    assert sha(database) == prep['database_sha256'] == candidates['database_sha256']
    for name, digest in prep['runtime_files'].items():
        assert sha(prepared / 'runtime' / name) == digest
    output = output or ROOT / 'results/vakra-world-mutation-search-v1'
    output.mkdir(exist_ok=False)
    changed_paths = {}
    for card in candidates['rows']:
        for index, candidate in enumerate(card['search']['candidates']):
            changed = output / f"task-{card['task_index']:03d}-mutation-{index:02d}.sqlite"
            shutil.copy2(database, changed)
            with sqlite3.connect(changed) as con:
                con.execute('PRAGMA foreign_keys=ON')
                apply(con, candidate['mutation'])
                assert not con.execute('PRAGMA foreign_key_check').fetchall()
                assert answer(con, card['target_sql']) == candidate['answer']
                assert candidate['answer'] != card['search']['original_answer']
            changed_paths[(card['uuid'], index)] = (changed, sha(changed))
    raw_root = ROOT / 'results/remote/vakra-coverage12-v1/runs/vakra-coverage12-v1'
    cards = {r['uuid']: r for r in candidates['rows']}
    queries = json.loads((prepared / 'queries.json').read_bytes())
    semaphore = asyncio.Semaphore(2)

    async def audit(source):
        async with semaphore:
            raw = json.loads(source.read_bytes())
            card = cards[raw['uuid']]
            assert len(raw['trace'][0]['input']) == 2
            assert [m['role'] for m in raw['trace'][0]['input']] == ['system', 'user']
            all_paths = sorted(source.parent.glob('case-*.json'))
            prior_paths = all_paths[:all_paths.index(source)]
            prior = [json.loads(p.read_bytes()) for p in prior_paths]
            first = json.loads(all_paths[0].read_bytes())['uuid']
            warm = next(q['uuid'] for q in queries if q['uuid'] != first)
            relative = source.relative_to(raw_root).as_posix()
            stem = relative.replace('/', '-').removesuffix('.json')
            report = {'source': relative, 'source_sha256': sha(source), 'uuid': raw['uuid'],
                'task_index': card['task_index'], 'original_termination': raw['termination'],
                'worker_prefix_sha256': {p.name: sha(p) for p in prior_paths}, 'trials': []}
            with (output / (stem + '.stderr.log')).open('x', encoding='utf-8') as log:
                baseline = await replay(prepared, database, raw, prior, warm, log)
                report['baseline_replay'] = baseline
                if not baseline['preserved'] or baseline['previous_independent_episode_differences']:
                    report['status'] = 'original_replay_mismatch'
                else:
                    report['status'] = 'no_witness_in_bounded_search'
                    for index, candidate in enumerate(card['search']['candidates']):
                        changed, digest = changed_paths[(raw['uuid'], index)]
                        result = await replay(prepared, changed, raw, prior, warm, log)
                        trial = {'candidate_index': index, 'database_sha256': digest, **result}
                        report['trials'].append(trial)
                        if result['preserved']:
                            assert result['observation_sha256'] == baseline['observation_sha256']
                            report['status'] = 'witness_found'
                            report['witness'] = {'mutation': candidate['mutation'],
                                'database': str(changed.relative_to(ROOT)), 'database_sha256': digest,
                                'target_sql': card['target_sql'],
                                'original_answer': card['search']['original_answer'],
                                'counterfactual_answer': candidate['answer'],
                                'observation_sha256': result['observation_sha256']}
                            break
            with (output / (stem + '.json')).open('x', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(json.dumps({'source': relative, 'status': report['status'], 'trials': len(report['trials'])}), flush=True)
            return report

    sources = [p for p in sorted(raw_root.glob('*/*/shard-0/case-*.json'))
               if json.loads(p.read_bytes())['uuid'] in cards]
    assert len(sources) == 4 * len(cards)
    rows = await asyncio.gather(*(audit(p) for p in sources))
    assert sha(database) == candidates['database_sha256']
    for path, digest in changed_paths.values():
        assert sha(path) == digest
    report = {'purpose': __doc__, 'candidate_file_sha256': sha(candidate_path),
        'script_sha256': sha(Path(__file__)), 'preparation_sha256': sha(prepared / 'preparation_manifest.json'),
        'episodes': len(rows), 'distinct_tasks': len(cards), 'mutant_databases': len(changed_paths),
        'statuses': dict(Counter(r['status'] for r in rows)), 'rows': rows,
        'candidate_contract': candidates['scope'],
        'scope': 'Known development traces; stop at first witness per episode. Original replay is mandatory. All initial peek fields, ordered schemas and every target-episode tool response content/isError are compared exactly. Previous independent episodes may change, but are absent from the target model input. No witness is inconclusive. No model was rerun and natural-language interpretation remains evaluator supplied.'}
    summary_path = summary_path or ROOT / 'research/evidence/vakra_world_mutation_search_v1.json'
    with summary_path.open('x', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps({'complete': True, 'statuses': report['statuses']}), flush=True)


if __name__ == '__main__':
    asyncio.run(main())
