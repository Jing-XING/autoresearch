"""Isolate the adapter-version change using real MCP and unchanged other dependencies."""
import asyncio
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import socket
import sys
import tempfile


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def main():
    os.environ['LANGCHAIN_TRACING_V2'] = 'false'
    os.environ['LANGSMITH_TRACING'] = 'false'
    attempts, socketpairs = [], []
    def guard(event, args):
        if event == 'socket.connect':
            caller = sys._getframe(1)
            if (caller.f_code.co_name == '_fallback_socketpair'
                and Path(caller.f_code.co_filename).resolve() == Path(socket.__file__).resolve()
                and args[1][0] in ('127.0.0.1','::1')):
                socketpairs.append(True)
                return
            attempts.append(event)
            raise PermissionError('Version probe permits stdio only')
    sys.addaudithook(guard)
    prior_path = Path('research/evidence/rac_real_mcp_probe_v1.json')
    prior = json.loads(prior_path.read_bytes())
    source = Path('results/third_party/rac/source')
    for name,digest in prior['source_sha256'].items():
        assert sha(source/name) == digest
    overlay = Path('results/third_party/rac/mcp-adapter-0.2.2').resolve()
    sys.path.insert(0,str(overlay))
    sys.path.insert(0,str((source/'src').resolve()))
    versions = dict(prior['packages'], **{'langchain-mcp-adapters':'0.2.2'})
    assert all(importlib.metadata.version(k) == v for k,v in versions.items())
    from react_agent_compensation.core.mcp.client import MCPCompensationClient
    from react_agent_compensation.core.extraction.state_mappers import StateMappersStrategy
    import langchain_mcp_adapters.tools as adapter_tools
    assert Path(adapter_tools.__file__).resolve().is_relative_to(overlay)
    server = Path('scripts/rac_mcp_fixture_server.py').resolve()
    assert sha(server) == prior['scripts_sha256'][str(server)]
    run = Path(tempfile.mkdtemp(prefix='version-022-',dir='results/probes/rac-mcp'))
    controls = [r for r in prior['cases'] if not r['legacy_raise_control']]
    rows = []
    for i, previous in enumerate(controls):
        route, mode = previous['route'], previous['behavior']
        state_path = (run/f'case-{i:02d}.json').resolve()
        state_path.write_text(json.dumps(dict(active=False,calls=[])),encoding='utf-8')
        config = {'fixture':dict(transport='stdio',command=sys.executable,
                  args=['-X','utf8',str(server),str(state_path),mode,'cancel' if route == 'rollback' else 'book'])}
        client = MCPCompensationClient(config, extraction_strategy=StateMappersStrategy(
            {'book':lambda result,params:{'booking_id':params['booking_id']}}))
        await client.connect()
        pairs = await client.get_compensation_pairs()
        raw = next(t for t in client._raw_tools if t.name == 'book')
        assert raw.args_schema.get('x-compensation-pair') == 'cancel'
        manager = client.recovery_manager
        added = manager.compensation_pairs.get('book') != 'cancel'
        if added:
            manager.add_compensation_pair('book','cancel')
        book = next(t for t in await client.get_tools() if t.name == 'book')
        params = {'booking_id':'fixture-1'}
        value = dict(type='tool_call',name='book',id='fixture-call',args=params) if route == 'forward_tool_call' else params
        error, success, result = None, None, None
        try:
            result = await book.ainvoke(value)
            if route == 'rollback':
                success = (await asyncio.to_thread(manager.rollback)).success
        except Exception as exc:
            error = dict(type=type(exc).__name__,message=str(exc))
        state = json.loads(state_path.read_bytes())
        records = list(manager.log.snapshot().values())
        assert len(records) == 1
        row = dict(route=route,behavior=mode,discovered_pairs=pairs,explicitly_added_pair=added,
            record_status=records[0].status.value,marked_compensated=records[0].compensated,
            rollback_reported_success=success,exception=error,fixture_state=state,
            forward_result_type=type(result).__name__,state_sha256=sha(state_path),
            default_032_comparison={k:previous[k] for k in
                ('record_status','marked_compensated','rollback_reported_success','exception')})
        rows.append(row)
        await client.close()
        print(json.dumps({k:row[k] for k in ('route','behavior','record_status','rollback_reported_success','exception')}),flush=True)
    assert len(rows) == 6 and not attempts
    for r in rows:
        assert r['discovered_pairs'] == {} and r['explicitly_added_pair']
        if r['route'] == 'rollback':
            assert [c['name'] for c in r['fixture_state']['calls']] == ['book','cancel']
            if r['behavior'] in ('explicit_error','server_exception'):
                assert r['exception']['type'] == 'CriticalFailure' and not r['marked_compensated']
                assert r['default_032_comparison']['marked_compensated']
            else:
                assert r['rollback_reported_success']
        else:
            assert r['record_status'] == 'FAILED' and r['exception']['type'] == 'ToolException'
            assert r['default_032_comparison']['record_status'] == 'COMPLETED'
    result = dict(purpose=__doc__,packages=versions,rac_revision=prior['rac_revision'],
        prior_probe_sha256=sha(prior_path),server_sha256=sha(server),script_sha256=sha(Path(__file__)),
        adapter_source_sha256=sha(Path(adapter_tools.__file__)),
        install_report_sha256=sha(Path('results/third_party/rac/mcp_adapter_022_install_report.json')),
        cases=rows,controls_passed=True,external_connection_attempts=len(attempts),
        allowed_stdlib_socketpairs=len(socketpairs),model_calls=0,
        limits=['Only adapter version changes; other packages remain current. This is not the original paper environment.',
                'Six matched constructed protocol executions, not model tasks or estimates of defect prevalence.',
                'Automatic discovery fails in both tested combinations; registration is explicitly added to isolate execution behavior.'])
    with Path('research/evidence/rac_mcp_adapter_version_probe_v1.json').open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2);stream.write('\n')


if __name__ == '__main__':
    asyncio.run(main())
