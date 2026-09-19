"""Bounded CPU probe of the author's unchanged recovery core and adapter.

All tool effects are an in-memory fixture. This is a software counterexample,
not an LLM benchmark, replication of the paper's performance, or new method.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import sys

REVISION = '068c327ab3f9b79a86a39503946e26320b74b97a'
TREE_SHA256 = '753fdb17e2565c53e708ff9badb7e4cd5196277c4e69765e49ee04a222e82490'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--tree', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    tree_raw = args.tree.read_bytes()
    if hashlib.sha256(tree_raw).hexdigest() != TREE_SHA256:
        raise ValueError('Source manifest differs from the recorded official Git tree')
    tree = json.loads(tree_raw)
    if tree.get('truncated'):
        raise ValueError('Incomplete source manifest')
    verified = {}
    for item in tree['tree']:
        if item['type'] != 'blob' or not item['path'].startswith('src/'):
            continue
        raw = (args.source / item['path']).read_bytes()
        git_sha = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        if git_sha != item['sha']:
            raise ValueError('Source differs from the fixed Git tree')
        verified[item['path']] = hashlib.sha256(raw).hexdigest()
    sys.path.insert(0, str((args.source / 'src').resolve()))
    from react_agent_compensation.core.recovery_manager import RecoveryManager
    from react_agent_compensation.core.protocols import SimpleActionResult
    from react_agent_compensation.core.extraction.state_mappers import StateMappersStrategy
    from react_agent_compensation.core.errors.explicit import ExplicitStatusStrategy

    # Load the unchanged adapter module directly; no LangChain model or client.
    path = args.source / 'src/react_agent_compensation/langchain_adaptor/adapters.py'
    spec = importlib.util.spec_from_file_location('rac_author_adapters_probe', path)
    adapters = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapters)

    class Fixture:
        def __init__(self, mode):
            self.mode = mode
            self.active = True
            self.calls = []

        def invoke(self, params):
            assert params == {'booking_id': 'fixture-1'}
            self.calls.append({'tool': 'cancel', 'params': params})
            if self.mode == 'raises':
                raise RuntimeError('Fixture compensation unavailable')
            if self.mode == 'error_payload':
                return {'status': 'error', 'error': 'Fixture cancellation denied'}
            if self.mode == 'success':
                self.active = False
            return {'status': 'success', 'cancelled': True}

    class DirectExecutor:
        def __init__(self, fixture, mode):
            self.fixture, self.mode = fixture, mode

        def execute(self, name, params):
            assert name == 'cancel'
            result = self.fixture.invoke(params)
            return SimpleActionResult(result, 'error' if self.mode == 'error_payload' else 'success', name)

    class StatusCheckedExecutor:
        """Diagnostic control, not a proposed research algorithm."""
        def __init__(self, executor):
            self.executor = executor

        def execute(self, name, params):
            result = self.executor.execute(name, params)
            if result.status == 'error':
                raise RuntimeError('Diagnostic control rejected explicit error status')
            content = result.content
            if isinstance(content, dict) and content.get('status') == 'error':
                raise RuntimeError('Diagnostic control rejected error payload')
            return result

    cases = []
    for adapter in ('direct_protocol', 'author_langchain_adapter', 'status_checked_author_adapter'):
        for mode in ('success', 'raises', 'error_payload', 'silent_noop'):
            fixture = Fixture(mode)
            executor = (DirectExecutor(fixture, mode) if adapter == 'direct_protocol' else
                        adapters.LangChainToolExecutor({'cancel': fixture}))
            if adapter == 'status_checked_author_adapter':
                executor = StatusCheckedExecutor(executor)
            manager = RecoveryManager(
                compensation_pairs={'book': 'cancel'}, action_executor=executor,
                error_strategy=ExplicitStatusStrategy(),
                extraction_strategy=StateMappersStrategy({'book': lambda result, params: {'booking_id': result['booking_id']}}),
            )
            record = manager.record_action('book', {'destination': 'synthetic'})
            manager.mark_completed(record.id, {'booking_id': 'fixture-1'})
            report, failure = None, None
            try:
                report = manager.rollback()
            except Exception as exc:
                failure = {'type': type(exc).__name__, 'message': str(exc)}
            after = manager.log.get(record.id)
            cases.append({'executor': adapter, 'compensation_behavior': mode,
                'fixture_active_before': True, 'fixture_active_after': fixture.active,
                'calls': fixture.calls, 'rollback_reported_success': report.success if report else False,
                'marked_compensated': after.compensated, 'record_status': after.status.value,
                'false_clean_report': bool(report and report.success and fixture.active), 'exception': failure})
    # Controls are fixed assertions about this deliberately constructed fixture.
    indexed = {(r['executor'], r['compensation_behavior']): r for r in cases}
    for adapter in ('direct_protocol', 'author_langchain_adapter', 'status_checked_author_adapter'):
        assert not indexed[adapter, 'success']['fixture_active_after']
        assert indexed[adapter, 'success']['rollback_reported_success']
    assert indexed['direct_protocol', 'raises']['exception']['type'] == 'CriticalFailure'
    assert indexed['author_langchain_adapter', 'raises']['false_clean_report']
    assert indexed['direct_protocol', 'error_payload']['false_clean_report']
    for mode in ('raises', 'error_payload'):
        assert not indexed['status_checked_author_adapter', mode]['false_clean_report']
    assert indexed['status_checked_author_adapter', 'silent_noop']['false_clean_report']
    result = {'purpose': __doc__, 'source_repo': 'https://github.com/wso2-incubator/research-rac',
        'source_revision': REVISION, 'source_tree_sha256': TREE_SHA256,
        'probe_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'source_files_sha256': verified,
        'python_version': sys.version, 'pydantic_version': importlib.metadata.version('pydantic'),
        'cases': cases, 'fixture_controls_passed': True, 'model_calls': 0,
        'limitations': ['Twelve constructed software cases, not a prevalence estimate or independent agent tasks',
                        'Uses unchanged author core and adapter with in-memory tool fixtures, not a live external service',
                        'Does not reproduce the original paper benchmark or imply all configurations fail',
                        'Explicit-status handling is a diagnostic software repair; silent no-op needs additional evidence']}
    with args.output.open('x', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
        f.write('\n')
    for row in cases:
        print(row['executor'], row['compensation_behavior'], 'residual=', row['fixture_active_after'],
              'reported_success=', row['rollback_reported_success'], 'false_clean=', row['false_clean_report'])


if __name__ == '__main__':
    main()
