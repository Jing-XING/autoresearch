"""Compare recovery records with native airline cancellation state over real MCP.

Two declared workflow fixtures x four fault placements x three client conditions.
No models, official task rewards, service credentials, or airline service calls.
"""
import asyncio
import ast
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import socket
import sys
import tempfile

from probe_independent_compensation import verify_source
from probe_rac_compensation_status import TREE_SHA256, REVISION
from tau_airline_compensation_fixture import observe


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract_reservation(result, params, decode_record_repr=False):
    value = getattr(result, 'content', result)
    if decode_record_repr and isinstance(value, dict) and set(value) == {'raw'}:
        assert isinstance(value['raw'], str) and len(value['raw']) < 100000
        value = ast.literal_eval(value['raw'])
    if isinstance(value, list):
        value = json.loads(next(x['text'] for x in value if x.get('type') == 'text'))
    elif isinstance(value, str):
        value = json.loads(value)
    elif isinstance(value, dict) and 'structuredContent' in value:
        value = value['structuredContent']
    return {'reservation_id': value['reservation_id']}


async def main():
    os.environ.update(LANGCHAIN_TRACING_V2='false', LANGSMITH_TRACING='false', PYTHON_DOTENV_DISABLED='1')
    attempts, socketpairs = [], []
    def guard(event, args):
        if event == 'socket.connect':
            caller = sys._getframe(1)
            if (caller.f_code.co_name == '_fallback_socketpair'
                    and Path(caller.f_code.co_filename).resolve() == Path(socket.__file__).resolve()
                    and args[1][0] in ('127.0.0.1', '::1')):
                socketpairs.append(True)
                return
            attempts.append(str(args[1]))
            raise PermissionError('Native airline comparison permits stdio only')
    sys.addaudithook(guard)
    agent_source, agent_manifest = verify_source('agent-saga', '4310ff570e60c42c081ae216e87a1ccb093525d4',
                                                 '108443abc43876916450442a0bbd4b3b9e69b8d0ca2f46ed05a1974d100a5176')
    rac_root = Path('results/third_party/rac')
    assert sha(rac_root/'tree.json') == TREE_SHA256
    rac_hashes = {}
    for entry in json.loads((rac_root/'tree.json').read_bytes())['tree']:
        if entry['type'] == 'blob' and entry['path'].startswith('src/'):
            data = (rac_root/'source'/entry['path']).read_bytes()
            assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest() == entry['sha']
            rac_hashes[entry['path']] = hashlib.sha256(data).hexdigest()
    sys.path.insert(0, str(agent_source.resolve()))
    sys.path.insert(0, str((rac_root/'source/src').resolve()))
    from agent_saga.mcp.proxy import SagaMCPProxy
    from agent_saga.mcp.policy import load_policy
    from agent_saga.mcp.stdio import UpstreamServer
    from agent_saga.wal import AsyncWAL
    from react_agent_compensation.core.mcp.client import MCPCompensationClient
    from react_agent_compensation.core.extraction.state_mappers import StateMappersStrategy
    from react_agent_compensation.core.mcp.tools import wrap_mcp_tools
    from langchain_mcp_adapters.client import MultiServerMCPClient
    expected = {'langchain-mcp-adapters': '0.3.2', 'langchain-core': '1.6.3', 'mcp': '1.30.0', 'pydantic': '2.13.5'}
    assert all(importlib.metadata.version(k) == v for k, v in expected.items())
    preflight = json.loads(Path('research/evidence/tau_airline_compensation_preflight_v1.json').read_bytes())
    bookings = {r['metadata']['profile']: r['booking'] for r in preflight['cases']}
    work = Path('results/probes/tau-airline-mcp')
    work.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='native-', dir=work)).resolve()
    server = Path('scripts/tau_airline_mcp_server.py').resolve()
    child_python = Path('C:/Users/xingjing/AppData/Local/Temp/tau2-research-env/Scripts/python.exe')
    policy = load_policy({'mode': 'enforce', 'tools': {'book_reservation': {
        'semantics': 'COMPENSABLE', 'compensate': {'tool': 'cancel_reservation',
                                                 'args': {'reservation_id': '$.structuredContent.reservation_id'}}}}})
    rows = []
    for profile in ('single_card', 'two_leg_mixed'):
        for mode in ('normal', 'native_error_before_effect', 'shadow_only', 'error_after_effect'):
            conditions = ['rac_default', 'rac_raise_control', 'agent_saga']
            if profile == 'single_card' and mode == 'normal':
                conditions.insert(0, 'rac_unadapted_mapper')
            for condition in conditions:
                state_path = run/f'{profile}-{mode}-{condition}.json'
                command = [str(child_python), '-X', 'utf8', str(server), str(state_path), profile, mode]
                common = {'profile': profile, 'fault': mode, 'condition': condition}
                if condition == 'agent_saga':
                    upstream = UpstreamServer(command)
                    wal_path = run/f'{profile}-{mode}-{condition}.wal.jsonl'
                    wal = AsyncWAL(wal_path)
                    await wal.start()
                    proxy = SagaMCPProxy(policy, upstream.call_tool, boundary='explicit', wal=wal)
                    await upstream.start()
                    try:
                        await upstream.request('initialize', {'protocolVersion': '2025-03-26', 'capabilities': {},
                                                            'clientInfo': {'name': 'native-domain-control', 'version': '1'}})
                        upstream.proc.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
                        await upstream.proc.stdin.drain()
                        schemas = await upstream.request('tools/list')
                        assert {t['name'] for t in schemas['tools']} == {'book_reservation', 'cancel_reservation'}
                        forward = await proxy.call('book_reservation', bookings[profile])
                        rid = forward['structuredContent']['reservation_id']
                        context = proxy._ctx
                        before_status = [s.state.value for s in context.stack]
                        rollback = await proxy.rollback('declared local experiment rollback boundary')
                        row = dict(common, reservation_id=rid, states_before=before_status,
                                   states_after=[s.state.value for s in context.stack], rollback_report=rollback,
                                   compensation_id_source='$.structuredContent.reservation_id',
                                   wal_file=str(wal_path), wal_sha256=sha(wal_path))
                    finally:
                        await proxy.close(failed=True)
                        await wal.close()
                        await upstream.close()
                else:
                    config = {'airline': {'transport': 'stdio', 'command': command[0], 'args': command[1:]}}
                    decode_repr = condition != 'rac_unadapted_mapper'
                    client = MCPCompensationClient(config, extraction_strategy=StateMappersStrategy({
                        'book_reservation': lambda result, params: extract_reservation(result, params, decode_repr)}))
                    await client.connect()
                    try:
                        discovered = await client.get_compensation_pairs()
                        manager = client.recovery_manager
                        explicit_pair = manager.compensation_pairs.get('book_reservation') != 'cancel_reservation'
                        if explicit_pair:
                            manager.add_compensation_pair('book_reservation', 'cancel_reservation')
                        if condition == 'rac_raise_control':
                            replacement = MultiServerMCPClient(config, handle_tool_errors=False)
                            client._raw_tools = await replacement.get_tools()
                            wrapped = wrap_mcp_tools(client._raw_tools, manager)
                        else:
                            wrapped = await client.get_tools()
                        book = next(t for t in wrapped if t.name == 'book_reservation')
                        forward = await book.ainvoke(bookings[profile])
                        rid = extract_reservation(forward, bookings[profile])['reservation_id']
                        before_status = [r.status.value for r in manager.log.snapshot().values()]
                        rollback, rollback_error = None, None
                        try:
                            rollback = await asyncio.to_thread(manager.rollback)
                        except Exception as exc:
                            rollback_error = {'type': type(exc).__name__, 'message': str(exc)}
                        records = list(manager.log.snapshot().values())
                        assert len(records) == 1
                        row = dict(common, reservation_id=rid, states_before=before_status,
                                   states_after=[r.status.value for r in records],
                                   rollback_report={'success': rollback.success if rollback is not None else None},
                                   rollback_exception=rollback_error,
                                   explicitly_added_pair=explicit_pair, discovered_pairs=discovered,
                                   compensation_id_source='parsed actual returned reservation JSON; stored raw Python-literal representation decoded' if decode_repr else 'actual returned reservation JSON parser without raw-record adaptation',
                                   decoded_stored_result_repr=decode_repr,
                                   action_record=records[0].model_dump(mode='json'),
                                   marked_compensated=records[0].compensated)
                    finally:
                        await client.close()
                state = json.loads(state_path.read_bytes())
                expected_calls = ['book_reservation'] if condition == 'rac_unadapted_mapper' else ['book_reservation', 'cancel_reservation']
                assert [r['name'] for r in state['calls']] == expected_calls
                oracle = observe(state['before'], state['current'], rid, bookings[profile])
                assert oracle['cancellation_contract_met'] == (mode in ('normal', 'error_after_effect') and condition != 'rac_unadapted_mapper')
                assert oracle['existing_reservations_unchanged']
                row.update(oracle=oracle, raw_state_file=str(state_path), raw_state_sha256=sha(state_path))
                rows.append(row)
                with (run/'case_records.jsonl').open('a', encoding='utf-8', newline='\n') as stream:
                    stream.write(json.dumps(row)+'\n')
                print(json.dumps(dict(common, states_after=row['states_after'], rollback_report=row['rollback_report'],
                                      cancellation_contract_met=oracle['cancellation_contract_met'])), flush=True)
    assert len(rows) == 25 and not attempts
    result = {'purpose': __doc__, 'cases': rows, 'rac_revision': REVISION, 'rac_source_sha256': rac_hashes,
              'agent_saga_source_manifest': agent_manifest, 'parent_packages': expected,
              'raw_directory': str(run), 'child_python': str(child_python),
              'scripts_sha256': {str(p): sha(p) for p in [Path(__file__), Path('scripts/tau_airline_mcp_server.py'), Path('scripts/tau_airline_compensation_fixture.py')]},
              'preflight_sha256': sha(Path('research/evidence/tau_airline_compensation_preflight_v1.json')),
              'parent_external_connection_attempts': attempts, 'allowed_stdlib_socketpairs': len(socketpairs),
              'child_external_network_blocked': True, 'model_calls': 0,
              'initial_attempt': {'script_snapshot': 'results/probes/tau-airline-mcp/probe_initial_attempt.py',
                  'sha256': sha(Path('results/probes/tau-airline-mcp/probe_initial_attempt.py')),
                  'raw_directory': 'results/probes/tau-airline-mcp/native-8teh6zte',
                  'reason': 'Strict intended-call assertion failed after one real booking: mapper expected actual adapter result, while RAC stored it as a raw string representation. Initial artifacts retained. Final grid adds an unadapted control and explicitly disclosed stored-result representation decoder; no upstream source patched.'},
              'second_attempt': {'script_snapshot': 'results/probes/tau-airline-mcp/probe_second_attempt.py',
                  'sha256': sha(Path('results/probes/tau-airline-mcp/probe_second_attempt.py')),
                  'raw_directory': 'results/probes/tau-airline-mcp/native-s9ukg969',
                  'reason': 'Harness did not catch the RAC raising-control CriticalFailure at rollback. Preserve exception/raw states; final harness records this as an exception outcome rather than assuming every rollback returns a report. Repeated controls are not extra observations.'},
              'limitations': ['Two constructed profiles on an official unit-test database, not a sampled task benchmark.',
                              'Fault placement is imposed; no prevalence or model efficacy estimate.',
                              'Cancellation contract is weaker than full database restoration; omitted seat release is documented upstream.',
                              'RAC pairs and agent-saga compensation policy are explicitly configured and disclosed.',
                              'RAC raising condition replaces its raw adapter client; it is a diagnostic control.',
                              'The outer agent-saga serve_stdio client loop is not used.']}
    out = Path('research/evidence/tau_airline_compensation_probe_v1.json')
    with out.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'completed_cases': len(rows), 'output': str(out)}), flush=True)


if __name__ == '__main__':
    async def bounded():
        async with asyncio.timeout(1200):
            await main()
    asyncio.run(bounded())
