"""Prepare the fixed new-domain pools and audit initial MCP observations on CPU."""
import asyncio
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autolab.vakra_prepare import prepare, sha
from autolab.vakra_mcp_audit import decode_result


async def main():
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client
    selection_path = ROOT / 'research/evidence/vakra_domain_expansion_download_v1.json'
    selection = json.loads(selection_path.read_bytes())
    root = ROOT / 'results/vakra-domain-expansion-v1'
    root.mkdir(exist_ok=False)
    records = []
    for entry in selection['selection']:
        domain = entry['domain']
        dest = root / domain
        manifest = prepare(ROOT / 'results/third_party/vakra', ROOT / 'results/third_party/vakra-data', domain, 'train', dest)
        qp = dest / 'queries.json'
        queries = json.loads(qp.read_bytes())
        queries.sort(key=lambda q: hashlib.sha256(('task-expansion-20260919:' + q['uuid']).encode()).hexdigest())
        assert [q['uuid'] for q in queries[:20]] == entry['selected_uuids']
        qp.write_text(json.dumps(queries, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        manifest.update(original_order_queries_sha256=manifest['prepared_queries_sha256'],
                        prepared_queries_sha256=sha(qp), ordering='SHA256(task-expansion-20260919: + UUID)',
                        expansion_selection_sha256=sha(selection_path))
        mp = dest / 'preparation_manifest.json'
        mp.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        params = StdioServerParameters(command=sys.executable,
            args=['-X', 'utf8', '-m', 'autolab.vakra_stdio', '--runtime', str(dest / 'runtime'),
                  '--database', str(dest / (domain + '.sqlite')), '--domain', domain], cwd=str(ROOT),
            env={'PYTHON_DOTENV_DISABLED': '1', 'PYTHONUTF8': '1', 'PYTHONPATH': str(ROOT)})
        rows = []
        with (root / (domain + '.stderr.log')).open('x', encoding='utf-8') as log:
            async with stdio_client(params, errlog=log) as (read, write):
                async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=60)) as session:
                    await session.initialize()
                    await session.call_tool('get_data', {'tool_universe_id': queries[1]['uuid']})
                    for q in queries[:20]:
                        row = {'uuid': q['uuid']}
                        try:
                            initial = decode_result(await session.call_tool('get_data', {'tool_universe_id': q['uuid']}))
                            schemas = [t.model_dump(mode='json') for t in (await session.list_tools()).tools]
                            row.update(initial_peek=initial, schemas=schemas)
                        except Exception as exc:
                            row.update(error_type=type(exc).__name__, error=str(exc))
                        rows.append(row)
        record = {'domain': domain, 'available_queries': len(queries), 'selected_task_ids': entry['selected_uuids'],
                  'preparation_sha256': sha(mp), 'database_sha256': manifest['database_sha256'],
                  'registered_episodes': len(rows) * 6, 'initialization_errors': sum('error' in r for r in rows),
                  'rows': rows}
        records.append(record)
        print(json.dumps({k: record[k] for k in ('domain', 'available_queries', 'registered_episodes', 'initialization_errors')}), flush=True)
    report = {'purpose': __doc__, 'selection_sha256': sha(selection_path), 'domains': records,
              'registered_episodes': sum(r['registered_episodes'] for r in records),
              'model_outputs_seen': False, 'all_selected_tasks_retained': True,
              'preparation_source_sha256': sha(ROOT / 'autolab/vakra_prepare.py'), 'script_sha256': sha(Path(__file__))}
    with (ROOT / 'research/evidence/vakra_domain_expansion_setup_v1.json').open('x', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    asyncio.run(main())
