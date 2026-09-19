"""Offline one-predicate repair diagnostic; not a model intervention result."""
import asyncio
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autolab.relational_mutations import answer
from autolab.vakra_mcp_audit import decode_result
from audit_vakra_mutation_search import calls, sha


async def main():
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client
    evidence = ROOT / 'research/evidence/vakra_publishing_contract_audit_v1.json'
    audit = json.loads(evidence.read_bytes())
    row = next(r for r in audit['rows'] if r['source'] == 'original/qwen3/shard-0/case-007.json')
    root = ROOT / 'results/remote/vakra-permissive-v1/runs/vakra-permissive-v1/book_publishing_company'
    source = root / row['source']
    raw = json.loads(source.read_bytes())
    assert sha(source) == row['source_sha256']
    prior = [json.loads(p.read_bytes()) for p in sorted(source.parent.glob('case-*.json')) if p.name < source.name]
    prepared = ROOT / 'results/vakra-book_publishing_company-replication-v1'
    queries = json.loads((prepared / 'queries.json').read_bytes())
    warm = next(q['uuid'] for q in queries if q['uuid'] != prior[0]['uuid'])
    original = prepared / 'book_publishing_company.sqlite'
    mutant = ROOT / row['witness']['database']
    expected_hashes = {'original': audit['rows'][0]['baseline_replay']['observation_sha256']}
    results = []
    out = ROOT / 'results/vakra-publishing-contract-repair-v1'
    out.mkdir(exist_ok=False)
    for label, database in [('original', original), ('mutant', mutant)]:
        before_hash = sha(database)
        params = StdioServerParameters(command=sys.executable,
            args=['-X', 'utf8', '-m', 'autolab.vakra_stdio', '--runtime', str(prepared / 'runtime'),
                  '--database', str(database), '--domain', 'book_publishing_company'], cwd=str(ROOT),
            env={'PYTHON_DOTENV_DISABLED': '1', 'PYTHONUTF8': '1', 'PYTHONPATH': str(ROOT)})
        with (out / f'{label}.stderr.log').open('x', encoding='utf-8') as log:
            async with stdio_client(params, errlog=log) as (read, write):
                async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=60)) as session:
                    await session.initialize()
                    await session.call_tool('get_data', {'tool_universe_id': warm})
                    for previous in prior:
                        await session.call_tool('get_data', {'tool_universe_id': previous['uuid']})
                        for event in calls(previous):
                            c = event['tool_call']; await session.call_tool(c['name'], c['arguments'])
                    await session.call_tool('get_data', {'tool_universe_id': raw['uuid']})
                    names = {t.name for t in (await session.list_tools()).tools}
                    assert 'select_data_equal_to' in names
                    records = []
                    for i, event in enumerate(calls(raw)):
                        c = json.loads(json.dumps(event['tool_call']))
                        if i == 0:
                            assert c['name'] == 'select_data_not_equal_to' and c['arguments']['value'] == 'Y'
                            c['name'] = 'select_data_equal_to'; c['arguments']['value'] = '0'
                        result = await session.call_tool(c['name'], c['arguments'])
                        assert not result.isError
                        records.append({'call': c, 'result': result.model_dump(mode='json'), 'decoded': decode_result(result)})
        assert sha(database) == before_hash
        titles, sales = records[1]['decoded'], records[2]['decoded']
        assert isinstance(titles, list) and isinstance(sales, list) and len(titles) == len(sales)
        produced = sorted({(t, s) for t, s in zip(titles, sales)}, key=lambda x: x[0])
        with sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True) as con:
            gold = sorted([tuple(r) for r in answer(con, row['witness']['target_sql'])], key=lambda x: x[0])
        assert produced == gold
        results.append({'database_condition': label, 'database_sha256': before_hash,
                        'tool_results': records, 'deduplicated_title_sales_pairs': produced,
                        'matches_frozen_sql': True})
    assert results[0]['deduplicated_title_sales_pairs'] != results[1]['deduplicated_title_sales_pairs']
    report = {'purpose': __doc__, 'audit_sha256': sha(evidence), 'source_sha256': sha(source),
              'script_sha256': sha(Path(__file__)), 'results': results,
              'limit': 'The evaluator supplied the correct predicate and paired getter outputs offline. No model generated this repair, no neural continuation was run, and no success-rate improvement is claimed. This only establishes that an existing public tool sequence can distinguish these two data worlds.'}
    p = ROOT / 'research/evidence/vakra_publishing_contract_repair_v1.json'
    with p.open('x', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(json.dumps({'complete': True, 'original_pairs': len(results[0]['deduplicated_title_sales_pairs']),
                      'mutant_pairs': len(results[1]['deduplicated_title_sales_pairs']), 'both_match_sql': True}))


if __name__ == '__main__':
    asyncio.run(main())
