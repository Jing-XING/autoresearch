"""Distinguish documented LangChain invocation envelopes from RAC integration failures."""
import hashlib
import importlib.metadata
import inspect
import json
import os
from pathlib import Path
import sys


def main():
    os.environ['LANGCHAIN_TRACING_V2'] = 'false'
    os.environ['LANGSMITH_TRACING'] = 'false'
    connections = []

    def deny_network(event, args):
        if event == 'socket.connect':
            connections.append(event)
            raise PermissionError('Local fixture prohibits network connections')

    sys.addaudithook(deny_network)
    assert importlib.metadata.version('langchain-core') == '1.6.3'
    from langchain_core.tools import StructuredTool, ToolException
    from langchain_core.messages import ToolMessage
    from langchain_core.tools import base

    rows = []
    for mode in ('success', 'handled_exception', 'unhandled_exception', 'error_payload'):
        for envelope in (False, True):
            calls = []

            def operation(value: str):
                calls.append(value)
                if mode in ('handled_exception', 'unhandled_exception'):
                    raise ToolException('fixture diagnostic')
                if mode == 'error_payload':
                    return {'status': 'error', 'reason': 'fixture diagnostic'}
                return 'fixture diagnostic'

            tool = StructuredTool.from_function(operation, description='Local fixture.',
                handle_tool_error=mode == 'handled_exception')
            arguments = {'value': 'fixture-only'}
            value = {'type': 'tool_call', 'id': 'fixture-call', 'name': 'operation', 'args': arguments} if envelope else arguments
            output, error = None, None
            try:
                result = tool.invoke(value)
                output = result.model_dump(mode='json') if isinstance(result, ToolMessage) else result
                kind = type(result).__name__
            except ToolException as exc:
                error = str(exc)
                kind = 'ToolException'
            assert calls == ['fixture-only']
            rows.append(dict(mode=mode, tool_call_envelope=envelope, result_type=kind,
                             result=output, exception=error))
    index = {(r['mode'], r['tool_call_envelope']): r for r in rows}
    assert index['success', False]['result'] == index['handled_exception', False]['result']
    assert index['success', True]['result']['status'] == 'success'
    assert index['handled_exception', True]['result']['status'] == 'error'
    for envelope in (False, True):
        assert index['unhandled_exception', envelope]['result_type'] == 'ToolException'
    assert index['error_payload', True]['result']['status'] == 'success'
    assert not connections
    source = Path(inspect.getfile(base))
    report = dict(purpose=__doc__, package='langchain-core', version='1.6.3',
        library_base_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        cases=rows, controls_passed=True, attempted_network_connections=len(connections),
        interpretation=[
            'Plain argument invocation deliberately returns raw handled-error content. A ToolCall envelope preserves its error status.',
            'The fixture gives successful and handled-error calls equal text to show content alone need not distinguish them. This is constructed, not a prevalence estimate.',
            'An arbitrary returned dict containing status:error is application data; LangChain does not automatically interpret it as a ToolException.',
            'These documented behaviors are not LangChain bugs. RAC must preserve and interpret the appropriate integration-level error signals.',
            'No model, external service, full agent benchmark, or new independent framework defect was tested.'])
    output = Path('research/evidence/langchain_error_envelope_probe_v1.json')
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps(dict(cases=len(rows), controls_passed=True, network_connections=len(connections))))


if __name__ == '__main__':
    main()
