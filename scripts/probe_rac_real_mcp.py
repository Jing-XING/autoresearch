"""Exercise unchanged RAC's client, wrapper and rollback through real stdio MCP."""
import asyncio
import hashlib
import importlib.metadata
import json
import os
import socket
from pathlib import Path
import sys
import tempfile

from probe_rac_compensation_status import TREE_SHA256, REVISION


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def main():
    os.environ['LANGCHAIN_TRACING_V2'] = 'false'
    os.environ['LANGSMITH_TRACING'] = 'false'
    attempts, stdlib_loopback_pairs = [], []
    def deny_network(event, args):
        if event == 'socket.connect':
            caller = sys._getframe(1)
            if (caller.f_code.co_name == '_fallback_socketpair'
                    and Path(caller.f_code.co_filename).resolve() == Path(socket.__file__).resolve()
                    and args[1][0] in ('127.0.0.1', '::1')):
                stdlib_loopback_pairs.append('asyncio socketpair')
                return
            attempts.append(event)
            raise PermissionError('Probe allows stdio only')
    sys.addaudithook(deny_network)
    versions = {'langchain-mcp-adapters':'0.3.2', 'langchain-core':'1.6.3', 'mcp':'1.30.0', 'pydantic':'2.13.5'}
    assert all(importlib.metadata.version(k) == v for k,v in versions.items())
    source = Path('results/third_party/rac/source')
    tree_path = Path('results/third_party/rac/tree.json')
    assert sha(tree_path) == TREE_SHA256
    hashes = {}
    for entry in json.loads(tree_path.read_bytes())['tree']:
        if entry['type'] == 'blob' and entry['path'].startswith('src/'):
            data = (source / entry['path']).read_bytes()
            assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == entry['sha']
            hashes[entry['path']] = hashlib.sha256(data).hexdigest()
    sys.path.insert(0, str((source/'src').resolve()))
    from react_agent_compensation.core.mcp.client import MCPCompensationClient
    from react_agent_compensation.core.extraction.state_mappers import StateMappersStrategy
    from langchain_mcp_adapters.client import MultiServerMCPClient

    work = Path('results/probes/rac-mcp')
    work.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='native-', dir=work))
    server = Path('scripts/rac_mcp_fixture_server.py').resolve()
    cases = [('rollback', mode, legacy) for legacy in (False, True)
             for mode in ('success', 'explicit_error', 'server_exception', 'silent_noop')]
    cases += [(route, 'explicit_error', legacy) for legacy in (False, True)
              for route in ('forward_args', 'forward_tool_call')]
    rows = []
    for i, (route, mode, legacy) in enumerate(cases):
        state_path = (run/f'case-{i:02d}.json').resolve()
        state_path.write_text(json.dumps(dict(active=False, calls=[])), encoding='utf-8')
        config = {'fixture': {'transport':'stdio', 'command':sys.executable,
                  'args':['-X','utf8',str(server),str(state_path),mode,'cancel' if route == 'rollback' else 'book']}}
        client = MCPCompensationClient(config, extraction_strategy=StateMappersStrategy(
            {'book':lambda result, params: {'booking_id':params['booking_id']}}))
        await client.connect()
        discovered = await client.get_compensation_pairs()
        raw_book = next(t for t in client._raw_tools if t.name == 'book')
        schema_pair = raw_book.args_schema.get('x-compensation-pair')
        manager = client.recovery_manager
        # Explicit diagnostic registration isolates execution semantics if discovery fails.
        added_pair = manager.compensation_pairs.get('book') != 'cancel'
        if added_pair:
            manager.add_compensation_pair('book', 'cancel')
        if legacy:
            # A separate diagnostic control: RAC's factory exposes no flag for this.
            other = MultiServerMCPClient(config, handle_tool_errors=False)
            client._raw_tools = await other.get_tools()
            from react_agent_compensation.core.mcp.tools import wrap_mcp_tools
            wrapped = wrap_mcp_tools(client._raw_tools, manager)
        else:
            wrapped = await client.get_tools()
        book = next(t for t in wrapped if t.name == 'book')
        params = {'booking_id':'fixture-1'}
        input_value = dict(type='tool_call', name='book', id='fixture-call', args=params) if route == 'forward_tool_call' else params
        error, forward_result, rollback_success = None, None, None
        try:
            forward_result = await book.ainvoke(input_value)
            if route == 'rollback':
                assert json.loads(state_path.read_bytes())['active']
                rollback_success = (await asyncio.to_thread(manager.rollback)).success
        except Exception as exc:
            error = dict(type=type(exc).__name__, message=str(exc))
        state = json.loads(state_path.read_bytes())
        records = list(manager.log.snapshot().values())
        assert len(records) == 1
        row = dict(route=route, behavior=mode, legacy_raise_control=legacy,
                   discovered_pairs=discovered, adapter_schema_compensation=schema_pair,
                   explicitly_added_pair=added_pair,
                   forward_result_type=type(forward_result).__name__,
                   forward_result_status=getattr(forward_result,'status',None),
                   forward_result_content=getattr(forward_result,'content',forward_result),
                   rollback_reported_success=rollback_success, exception=error,
                   record_status=records[0].status.value, marked_compensated=records[0].compensated,
                   fixture_state=state, state_sha256=sha(state_path))
        rows.append(row)
        await client.close()
        print(json.dumps({k:row[k] for k in ('route','behavior','legacy_raise_control','record_status','rollback_reported_success','exception')}), flush=True)
    assert not attempts
    result = dict(purpose=__doc__, rac_revision=REVISION, packages=versions, cases=rows,
        source_sha256=hashes, scripts_sha256={str(p):sha(p) for p in (Path(__file__),server)},
        install_report_sha256=sha(Path('results/third_party/rac/mcp_install_report.json')),
        parent_network_connection_attempts=len(attempts), child_network_connections_prohibited=True,
        allowed_stdlib_loopback_socketpairs=len(stdlib_loopback_pairs),
        model_calls=0, raw_fixture_directory=str(run),
        limits=['Real SDK serialization, client discovery and RAC execution, but constructed local tools, not a model benchmark.',
                'Any manually added compensation pair is reported; it is not successful automatic discovery.',
                'Legacy raising is a diagnostic raw-client replacement, not a flag exposed by the RAC factory.',
                'Current dependency versions; no reconstruction of original paper environment or prevalence estimate.'])
    output = Path('research/evidence/rac_real_mcp_probe_v1.json')
    with output.open('x',encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    asyncio.run(main())
