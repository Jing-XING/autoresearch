"""Exercise pinned RAC with real StructuredTool and ToolMessage classes, no LLM."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import sys

from probe_rac_compensation_status import REVISION, TREE_SHA256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'tree', 'install-report', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    os.environ['LANGCHAIN_TRACING_V2'] = 'false'
    os.environ['LANGSMITH_TRACING'] = 'false'
    attempted_connections = []

    def deny_network(event, values):
        if event == 'socket.connect':
            attempted_connections.append('blocked')
            raise PermissionError('CPU fixture prohibits network connections')

    sys.addaudithook(deny_network)
    assert importlib.metadata.version('langchain-core') == '1.6.3'
    from langchain_core.messages import ToolMessage
    from langchain_core.tools import StructuredTool, ToolException

    raw = args.tree.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == TREE_SHA256
    tree = json.loads(raw)
    assert not tree['truncated']
    hashes = {}
    for entry in tree['tree']:
        if entry['type'] != 'blob' or not entry['path'].startswith('src/'):
            continue
        data = (args.source / entry['path']).read_bytes()
        assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == entry['sha']
        hashes[entry['path']] = hashlib.sha256(data).hexdigest()
    sys.path.insert(0, str((args.source / 'src').resolve()))
    from react_agent_compensation.core.config import RetryPolicy
    from react_agent_compensation.core.extraction.state_mappers import StateMappersStrategy
    from react_agent_compensation.core.recovery_manager import RecoveryManager

    def load_original(name):
        path = args.source / f'src/react_agent_compensation/langchain_adaptor/{name}.py'
        spec = importlib.util.spec_from_file_location('rac_real_tools_' + name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    adapters, interceptors = load_original('adapters'), load_original('interceptors')
    modes = ['success', 'runtime_exception', 'tool_exception', 'handled_tool_exception',
             'error_message', 'error_payload', 'silent_noop']
    rows = []
    for route in ('rollback', 'retry', 'alternative'):
        for mode in modes:
            state = {'effect': False, 'calls': 0}

            def operation(booking_id: str):
                assert booking_id == 'fixture-1'
                state['calls'] += 1
                if mode == 'runtime_exception':
                    raise RuntimeError('timeout: fixture tool unavailable')
                if mode in ('tool_exception', 'handled_tool_exception'):
                    raise ToolException('timeout: fixture tool unavailable')
                if mode == 'error_message':
                    return ToolMessage(content='Fixture operation rejected', status='error',
                                       tool_call_id='fixture-inner-call', name='operation')
                if mode == 'error_payload':
                    return {'status': 'error', 'error': 'Fixture operation rejected'}
                if mode == 'success':
                    state['effect'] = True
                return {'status': 'success', 'booking_id': booking_id}

            tool = StructuredTool.from_function(operation, name='operation',
                description='Execute one local in-memory fixture operation.',
                handle_tool_error=mode == 'handled_tool_exception')
            executor = adapters.LangChainToolExecutor({'cancel': tool})
            manager = RecoveryManager(compensation_pairs={'book': 'cancel'},
                alternative_map={'book': ['backup']} if route == 'alternative' else {},
                retry_policy=RetryPolicy(max_retries=2 if route == 'retry' else 0,
                                         initial_delay=0.001, max_delay=0.001, jitter=False),
                action_executor=executor,
                extraction_strategy=StateMappersStrategy(
                    {'book': lambda result, params: {'booking_id': result['booking_id']}}),
                enable_tool_alternatives=False)
            error = None
            message_status = None
            nested_status = None
            if route == 'rollback':
                record = manager.record_action('book', {})
                manager.mark_completed(record.id, {'booking_id': 'fixture-1'})
                report = manager.rollback()
                success = report.success
            else:
                interceptor = interceptors.ToolCallInterceptor(manager, {'book': tool, 'backup': tool})

                def initial_failure():
                    raise RuntimeError('timeout: initial action did not take effect')

                report = interceptor.intercept('book', {'booking_id': 'fixture-1'},
                                               'fixture-outer-call', initial_failure)
                success = report.success
                error = report.error
                nested_status = getattr(report.result, 'status', None)
                message = report.to_tool_message('fixture-outer-call', 'book')
                assert isinstance(message, ToolMessage)
                message_status = message.status
            records = list(manager.log.snapshot().values())
            assert len(records) == 1 and state['calls'] == 1
            rows.append(dict(route=route, behavior=mode, handle_tool_error=tool.handle_tool_error,
                effect_occurred=state['effect'], calls=state['calls'], reported_success=success,
                converted_tool_message_status=message_status, nested_result_status=nested_status,
                error=error, record_status=records[0].status.value,
                marked_compensated=records[0].compensated,
                false_success=success and not state['effect']))
    lookup = {(r['route'], r['behavior']): r for r in rows}
    for route in ('rollback', 'retry', 'alternative'):
        assert lookup[route, 'success']['effect_occurred']
        assert lookup[route, 'success']['reported_success']
        assert lookup[route, 'error_message']['false_success']
        assert lookup[route, 'handled_tool_exception']['false_success']
    for route in ('retry', 'alternative'):
        assert not lookup[route, 'runtime_exception']['reported_success']
        assert not lookup[route, 'tool_exception']['reported_success']
        assert lookup[route, 'error_message']['nested_result_status'] == 'error'
        assert lookup[route, 'error_message']['converted_tool_message_status'] == 'success'
    assert not attempted_connections
    install = json.loads(args.install_report.read_bytes())
    packages = {r['metadata']['name']: dict(version=r['metadata']['version'],
                sha256=r['download_info']['archive_info']['hashes']['sha256']) for r in install['install']}
    result = dict(purpose=__doc__, revision=REVISION, source_tree_sha256=TREE_SHA256,
        source_files_sha256=hashes, script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        python=sys.version, installed_wheels=packages, cases=rows, fixture_controls_passed=True,
        model_calls=0, attempted_network_connections=len(attempted_connections),
        limits=['Actual langchain-core tools/messages; no full LangGraph agent or external service',
                'Twenty-one selected fixtures within one RAC revision, not independent framework samples',
                'Same error-semantics mechanism as earlier probes, not 21 new discovered bugs',
                'LangChain handles ToolException by design; the tested integration must preserve its meaning'])
    with args.output.open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps({'cases': len(rows), 'controls_passed': True, 'network_connections': 0,
        'actual_error_message_conversion': [lookup[r, 'error_message'] for r in ('retry', 'alternative')]}))


if __name__ == '__main__':
    main()
