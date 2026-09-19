"""Execute two independent recovery implementations without models or services.

SagaLLM receives scripted agents through its coordinator interface. agent-saga
uses its unchanged MCP transport against the same real SDK fixture used for RAC.
These are selected mechanism controls, not a task benchmark or prevalence study.
"""
import asyncio
import contextlib
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import socket
import sys
import tempfile


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_source(name, revision, tree_sha):
    root = Path('results/third_party') / name
    manifest = json.loads((root / 'source_manifest.json').read_bytes())
    assert manifest['commit'] == revision
    assert sha(root / 'tree.json') == tree_sha
    tree = {x['path']:x for x in json.loads((root / 'tree.json').read_bytes())['tree'] if x['type'] == 'blob'}
    for rel, digest in manifest['files'].items():
        p = root / 'source' / rel
        blob = p.read_bytes()
        assert sha(p) == digest
        assert hashlib.sha1(b'blob ' + str(len(blob)).encode() + b'\0' + blob).hexdigest() == tree[rel]['sha']
    return root / 'source', manifest


def sagallm_cases(source):
    sys.path.insert(0, str((source / 'src').resolve()))
    import_log = io.StringIO()
    with contextlib.redirect_stdout(import_log):
        from multi_agent.saga import Saga

    rows = []
    cases = [('rollback', mode) for mode in ('success', 'returned_error', 'raised_error', 'silent_noop')]
    cases += [('forward', mode) for mode in ('raise_before_effect', 'raise_after_effect')]
    for route, mode in cases:
        state = {'active': False, 'events': []}
        class ScriptedAgent:
            def __init__(self, name, failing=False):
                self.name, self.failing = name, failing
                self.dependencies, self.dependents = [], []

            def run(self):
                state['events'].append(self.name + ':run')
                if self.failing or (route == 'forward' and mode == 'raise_before_effect'):
                    raise RuntimeError('Explicit constructed forward failure')
                state['active'] = True
                if route == 'forward':
                    raise RuntimeError('Constructed failure after the local effect')
                return {'booking_id': 'fixture-1', 'status': 'success'}

            def rollback(self):
                state['events'].append(self.name + ':rollback')
                if mode == 'raised_error':
                    raise RuntimeError('Constructed compensation exception')
                if mode == 'returned_error':
                    return {'status': 'error', 'error': 'Constructed compensation failure'}
                if mode == 'silent_noop':
                    return {'status': 'success'}
                state['active'] = False
                return {'status': 'success'}

        booking, failing = ScriptedAgent('booking'), ScriptedAgent('downstream', failing=True)
        if route == 'rollback':
            booking.dependents = [failing]
            failing.dependencies = [booking]
        saga = Saga()
        log = io.StringIO()
        exception = None
        with contextlib.redirect_stdout(log):
            saga.transaction_manager([booking, failing] if route == 'rollback' else [booking])
            try:
                saga.saga_coordinator(with_rollback=True)
            except Exception as exc:
                exception = dict(type=type(exc).__name__, message=str(exc))
        assert exception is None, 'Coordinator did not reach the intended failure scenario'
        expected = ['booking:run', 'downstream:run', 'booking:rollback'] if route == 'rollback' else ['booking:run']
        assert state['events'] == expected, 'Fixture execution path mismatch'
        rows.append(dict(route=route, behavior=mode, fixture_state=state,
                         coordinator_context=saga.context, raised_to_caller=exception,
                         stdout=log.getvalue(),
                         printed_rolled_back='Rolled back: booking' in log.getvalue()))
    return rows, import_log.getvalue()


async def agent_saga_cases(source, run):
    sys.path.insert(0, str(source.resolve()))
    from agent_saga.mcp.proxy import SagaMCPProxy
    from agent_saga.mcp.policy import load_policy
    from agent_saga.mcp.stdio import UpstreamServer
    from agent_saga.wal import AsyncWAL
    server = Path('scripts/rac_mcp_fixture_server.py').resolve()
    server_python = Path('results/venvs/rac-mcp/Scripts/python.exe').resolve()
    policy = load_policy({'mode':'enforce', 'tools': {
        'book': {'semantics':'COMPENSABLE', 'compensate': {
            'tool':'cancel', 'from_arguments': {'booking_id':'$.booking_id'}}}}})
    rows = []
    for route in ('rollback', 'forward'):
        for mode in ('success', 'explicit_error', 'server_exception', 'silent_noop'):
            state = (run / f'agent-saga-{route}-{mode}.json').resolve()
            state.write_text(json.dumps(dict(active=False, calls=[])), encoding='utf-8')
            wal_path = run / f'agent-saga-{route}-{mode}.wal.jsonl'
            upstream = UpstreamServer([str(server_python), '-X', 'utf8', str(server),
                                       str(state), mode, 'cancel' if route == 'rollback' else 'book'])
            wal = AsyncWAL(wal_path)
            await wal.start()
            proxy = SagaMCPProxy(policy, upstream.call_tool, boundary='explicit', wal=wal)
            forward_error = None
            result = None
            await upstream.start()
            try:
                initialization = await asyncio.wait_for(upstream.request('initialize', {
                    'protocolVersion':'2025-03-26', 'capabilities': {},
                    'clientInfo':{'name':'independent-recovery-probe', 'version':'1'}}), 20)
                upstream.proc.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
                await upstream.proc.stdin.drain()
                schemas = await asyncio.wait_for(upstream.request('tools/list'), 20)
                assert {x['name'] for x in schemas['tools']} == {'book', 'cancel'}
                try:
                    async with asyncio.timeout(20):
                        result = await proxy.call('book', {'booking_id':'fixture-1'})
                except Exception as exc:
                    forward_error = dict(type=type(exc).__name__, message=str(exc))
                context = proxy._ctx
                before = [s.state.value for s in context.stack]
                before_state = json.loads(state.read_bytes())
                async with asyncio.timeout(20):
                    rollback = await proxy.rollback('explicit experimental rollback boundary')
                after = [s.state.value for s in context.stack]
                current = json.loads(state.read_bytes())
                rows.append(dict(route=route, behavior=mode, initialize_result=initialization,
                    declared_policy={'compensation':'cancel', 'booking_id_source':'forward arguments'},
                    tool_schemas=schemas, forward_result=result, forward_exception=forward_error,
                    states_before_rollback=before, fixture_before_rollback=before_state,
                    rollback_report=rollback, states_after_rollback=after,
                    fixture_state=current, state_sha256=sha(state),
                    wal_file=str(wal_path), wal_sha256=sha(wal_path)))
            finally:
                try:
                    await proxy.close(failed=True)
                finally:
                    await wal.close()
                    await upstream.close()
            print(json.dumps({k:rows[-1][k] for k in ('route','behavior','states_before_rollback','rollback_report','states_after_rollback')}), flush=True)
    return rows


async def main():
    attempts, loopbacks = [], []
    def deny_network(event, args):
        if event == 'socket.connect':
            caller = sys._getframe(1)
            if (caller.f_code.co_name == '_fallback_socketpair'
                    and Path(caller.f_code.co_filename).resolve() == Path(socket.__file__).resolve()
                    and args[1][0] in ('127.0.0.1', '::1')):
                loopbacks.append('stdlib socketpair')
                return
            attempts.append(str(args[1]))
            raise PermissionError('Local recovery study permits stdio only')
    sys.addaudithook(deny_network)
    sagallm, m1 = verify_source('sagallm', '2781c33edc4005b066671d5dc3cad157fae14f11',
                              '14905162d0902642104d38aaf4740c2fa2f904429c5660360cf6f0dddf4a176d')
    agent_saga, m2 = verify_source('agent-saga', '4310ff570e60c42c081ae216e87a1ccb093525d4',
                                 '108443abc43876916450442a0bbd4b3b9e69b8d0ca2f46ed05a1974d100a5176')
    rows1, import_log = sagallm_cases(sagallm)
    work = Path('results/probes/rac-mcp')
    run = Path(tempfile.mkdtemp(prefix='independent-', dir=work))
    rows2 = await agent_saga_cases(agent_saga, run)
    assert not attempts
    report = dict(purpose=__doc__, source_manifests=[m1,m2], sagallm_cases=rows1,
                  sagallm_import_stdout=import_log, agent_saga_mcp_cases=rows2,
                  script_sha256=sha(Path(__file__)), fixture_script_sha256=sha(Path('scripts/rac_mcp_fixture_server.py')),
                  packages={n:importlib.metadata.version(n) for n in ('colorama','graphviz','pydantic','pydantic-core','typing-extensions','typing-inspection','annotated-types')},
                  environment_adaptation='Initial import failed because agent-saga retry.py imports undeclared pydantic; installed pydantic 2.13.5 without changing source. No MCP cases ran on that failed attempt.',
                  harness_correction='An initial harness omitted wal.start() and failed before the first forward tool call. Final harness follows the upstream CLI lifecycle; that setup failure is not a framework compensation result.',
                  child_python=str(Path('results/venvs/rac-mcp/Scripts/python.exe').resolve()),
                  parent_external_connection_attempts=attempts, allowed_stdlib_socketpairs=len(loopbacks),
                  child_external_network_blocked=True, model_calls=0,
                  limits=['Selected software mechanisms, not independent model tasks or a framework ranking.',
                          'SagaLLM uses scripted duck-typed agents, not its model-driven Agent implementation.',
                          'A generic returned error dictionary is not an advertised SagaLLM error protocol.',
                          'agent-saga uses actual upstream stdio and SDK server; the outer serve_stdio client loop is not invoked.',
                          'Compensation policy and explicit rollback boundary are supplied by the experimenter.',
                          'No crash durability, connector-service or arbitrary postcondition guarantee is tested.'])
    report['superseded_attempt'] = {
        'file':'research/evidence/independent_compensation_probe_v1.json',
        'sha256':sha(Path('research/evidence/independent_compensation_probe_v1.json')),
        'source_snapshot_sha256':sha(Path('results/probes/rac-mcp/independent_compensation_probe_source_v1.py')),
        'reason':'Two forward SagaLLM fixtures retained a dependent omitted from the registered graph, causing topological-sort KeyError before run. Corrected only the fixture graph; no framework source changed. All cases repeated and are not additional independent evidence.'}
    target = Path('research/evidence/independent_compensation_probe_v2.json')
    with target.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(report,stream,ensure_ascii=False,indent=2)
        stream.write('\n')
    print(json.dumps({'sagallm_cases':len(rows1),'agent_saga_mcp_cases':len(rows2),'output':str(target)}))


if __name__ == '__main__':
    asyncio.run(main())
