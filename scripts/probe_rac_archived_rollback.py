"""Test the author's published Zenodo source, separate from the newer Git revision."""
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import sys
import zipfile

ARCHIVE_SHA = '6faee4dedc04c242922d3b4fcf4bed5521e3b824d42ee1ad88c48be538d7cad4'
PREFIX = 'Kavirubc-react-agent-compensation-12e6678/src/'


def main():
    os.environ['LANGCHAIN_TRACING_V2'] = 'false'
    os.environ['LANGSMITH_TRACING'] = 'false'
    connections = []

    def deny_network(event, args):
        if event == 'socket.connect':
            connections.append(event)
            raise PermissionError('Archived-source fixture prohibits network connections')

    sys.addaudithook(deny_network)
    archive = Path('results/third_party/rac/zenodo-19753969.zip')
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == ARCHIVE_SHA
    destination = Path('results/third_party/rac/zenodo-source')
    source_hashes = {}
    with zipfile.ZipFile(archive) as zipped:
        for name in zipped.namelist():
            if not name.startswith(PREFIX) or not name.endswith('.py'):
                continue
            relative = PurePosixPath(name[len(PREFIX):])
            assert not relative.is_absolute() and '..' not in relative.parts
            data = zipped.read(name)
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                assert target.read_bytes() == data
            else:
                target.write_bytes(data)
            source_hashes[str(relative)] = hashlib.sha256(data).hexdigest()
    assert len(source_hashes) == 62
    sys.path.insert(0, str(destination.resolve()))
    from react_agent_compensation.core.recovery_manager import RecoveryManager
    from react_agent_compensation.core.protocols import SimpleActionResult
    from react_agent_compensation.core.extraction.state_mappers import StateMappersStrategy
    from react_agent_compensation.core.errors.explicit import ExplicitStatusStrategy
    from langchain_core.messages import ToolMessage
    from langchain_core.tools import StructuredTool, ToolException

    assert importlib.metadata.version('langchain-core') == '1.6.3'
    adapter_path = destination / 'react_agent_compensation/langchain_adaptor/adapters.py'
    spec = importlib.util.spec_from_file_location('archived_rac_adapters', adapter_path)
    adapters = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapters)
    modes = ('success', 'runtime_exception', 'tool_exception', 'handled_tool_exception',
             'error_message', 'error_payload', 'silent_noop')
    rows = []
    for executor_kind in ('direct_protocol', 'author_langchain_adapter'):
        for mode in modes:
            state = dict(active=False, forward_calls=0, compensation_calls=0)

            def book():
                state['forward_calls'] += 1
                state['active'] = True
                return {'booking_id': 'fixture-1'}

            def cancel(booking_id: str):
                assert booking_id == 'fixture-1'
                state['compensation_calls'] += 1
                if mode == 'runtime_exception':
                    raise RuntimeError('Fixture cancellation unavailable')
                if mode in ('tool_exception', 'handled_tool_exception'):
                    raise ToolException('Fixture cancellation unavailable')
                if mode == 'error_message':
                    return ToolMessage(content='Fixture cancellation denied',
                                       status='error', tool_call_id='fixture-cancel')
                if mode == 'error_payload':
                    return {'status':'error', 'error':'Fixture cancellation denied'}
                if mode == 'success':
                    state['active'] = False
                return {'status':'success', 'cancelled':True}

            tool = StructuredTool.from_function(cancel, description='Local in-memory cancellation fixture.',
                handle_tool_error=mode == 'handled_tool_exception')

            class DirectExecutor:
                def execute(self, name, params):
                    assert name == 'cancel'
                    content = tool.invoke(params)
                    return SimpleActionResult(content, 'error' if mode == 'error_payload' else 'success', name)

            executor = DirectExecutor() if executor_kind == 'direct_protocol' else adapters.LangChainToolExecutor({'cancel':tool})
            manager = RecoveryManager(compensation_pairs={'book':'cancel'}, action_executor=executor,
                error_strategy=ExplicitStatusStrategy(), extraction_strategy=StateMappersStrategy(
                    {'book':lambda result,params:{'booking_id':result['booking_id']}}))
            record = manager.record_action('book', {})
            manager.mark_completed(record.id, book())
            error, success = None, False
            try:
                success = manager.rollback().success
            except Exception as exc:
                error = dict(type=type(exc).__name__, message=str(exc))
            saved = manager.log.get(record.id)
            assert state['forward_calls'] == state['compensation_calls'] == 1
            rows.append(dict(executor=executor_kind, compensation_behavior=mode, **state,
                reported_success=success, marked_compensated=saved.compensated,
                record_status=saved.status.value, exception=error,
                false_clean_report=success and state['active']))
    index = {(r['executor'],r['compensation_behavior']):r for r in rows}
    for executor_kind in ('direct_protocol', 'author_langchain_adapter'):
        assert index[executor_kind,'success']['reported_success']
        assert not index[executor_kind,'success']['active']
        assert index[executor_kind,'error_payload']['false_clean_report']
    for mode in ('runtime_exception','tool_exception'):
        assert index['direct_protocol',mode]['exception']['type'] == 'CriticalFailure'
        assert index['author_langchain_adapter',mode]['false_clean_report']
    assert not connections
    result = dict(purpose=__doc__, author_artifact='https://zenodo.org/records/19753969',
        archive_sha256=ARCHIVE_SHA, archive_source_root=PREFIX, source_files_sha256=source_hashes,
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        python=sys.version, packages={n:importlib.metadata.version(n) for n in ('pydantic','langchain-core')},
        cases=rows, controls_passed=True, attempted_network_connections=len(connections), model_calls=0,
        limits=['Unchanged published archival source, with current isolated LangChain 1.6.3; not a reconstruction of original dependency versions.',
                'Fourteen selected local rollback fixtures, not the published model benchmark or fourteen distinct defects.',
                'Does not show this bug occurred in the archived experimental trajectories; their conservative status audit found no instance.',
                'Same compensation-result mechanism as the newer-revision probes; no independent method or prevalence claim.'])
    with Path('research/evidence/rac_archived_rollback_probe_v1.json').open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2)
        stream.write('\n')
    print(json.dumps(dict(cases=len(rows), controls_passed=True, network_attempts=len(connections))))


if __name__ == '__main__':
    main()
