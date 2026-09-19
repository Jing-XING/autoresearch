"""Check whether original RAC interception preserves recovery error statuses.

Constructed CPU fixtures only. No model calls, external effects, prevalence
estimate, or replication of the paper's benchmark.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import sys

from probe_rac_compensation_status import REVISION, TREE_SHA256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'tree', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
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
    from react_agent_compensation.core.errors.explicit import ExplicitStatusStrategy
    from react_agent_compensation.core.protocols import SimpleActionResult
    from react_agent_compensation.core.recovery_manager import RecoveryManager

    path = args.source / 'src/react_agent_compensation/langchain_adaptor/interceptors.py'
    spec = importlib.util.spec_from_file_location('rac_original_interceptor_probe', path)
    original = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original)

    class RecoveryTool:
        def __init__(self, mode, check):
            self.mode, self.check = mode, check
            self.effect = False
            self.calls = 0

        def invoke(self, params):
            assert params == {'booking_id': 'fixture-1'}
            self.calls += 1
            if self.mode == 'raises':
                raise RuntimeError('timeout: fixture recovery unavailable')
            if self.mode == 'success':
                self.effect = True
            status = 'error' if self.mode == 'error_status' else 'success'
            result = SimpleActionResult({'booking_id': 'fixture-1'}, status, 'book')
            if self.check == 'status' and result.status == 'error':
                raise RuntimeError('Diagnostic error-status rejection')
            if self.check == 'fixture_postcondition' and not self.effect:
                raise RuntimeError('Diagnostic fixture-state rejection')
            return result

    def initial_failure():
        raise RuntimeError('timeout: initial call failed before taking effect')

    cases = []
    for route in ('retry', 'alternative'):
        for check in ('none', 'status', 'fixture_postcondition'):
            for mode in ('success', 'raises', 'error_status', 'silent_noop'):
                tool = RecoveryTool(mode, check)
                manager = RecoveryManager(
                    compensation_pairs={'book': 'cancel'},
                    alternative_map={'book': ['backup']} if route == 'alternative' else {},
                    # Original strategy stops at attempt >= max_retries and starts at 1.
                    retry_policy=RetryPolicy(max_retries=2 if route == 'retry' else 0,
                                             initial_delay=0.001, max_delay=0.001, jitter=False),
                    error_strategy=ExplicitStatusStrategy(),
                    enable_tool_alternatives=False,
                )
                interceptor = original.ToolCallInterceptor(
                    rc_manager=manager, tools_cache={'book': tool, 'backup': tool},
                    error_detector=ExplicitStatusStrategy(),
                )
                result = interceptor.intercept('book', {'booking_id': 'fixture-1'},
                                               'fixture-call', initial_failure)
                records = list(manager.log.snapshot().values())
                assert len(records) == 1 and tool.calls == 1
                returned_status = getattr(result.result, 'status', None)
                cases.append(dict(route=route, diagnostic_check=check, behavior=mode,
                    actual_effect=tool.effect, recovery_calls=tool.calls,
                    interceptor_success=result.success, recovered=result.recovered,
                    action_taken=result.action_taken, result_status=returned_status,
                    record_status=records[0].status.value,
                    false_success=bool(result.success and not tool.effect)))
    indexed = {(r['route'], r['diagnostic_check'], r['behavior']): r for r in cases}
    for route in ('retry', 'alternative'):
        for check in ('none', 'status', 'fixture_postcondition'):
            assert indexed[route, check, 'success']['interceptor_success']
            assert not indexed[route, check, 'raises']['interceptor_success']
        failed = indexed[route, 'none', 'error_status']
        assert failed['false_success'] and failed['result_status'] == 'error'
        assert not indexed[route, 'status', 'error_status']['false_success']
        assert indexed[route, 'status', 'silent_noop']['false_success']
        assert not indexed[route, 'fixture_postcondition', 'silent_noop']['false_success']
    report = dict(purpose=__doc__, source_repo='https://github.com/wso2-incubator/research-rac',
        revision=REVISION, source_tree_sha256=TREE_SHA256, source_files_sha256=hashes,
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        python=sys.version, pydantic=importlib.metadata.version('pydantic'),
        cases=cases, fixture_controls_passed=True, model_calls=0,
        limitations=[
            'Twenty-four selected deterministic fixtures within the same implementation, not independent tasks',
            'Original ToolCallInterceptor and RecoveryManager, but no full LangChain agent or external service',
            'State-check control has exact access to this in-memory fixture; no claim of a deployable general verifier',
            'LLM alternative discovery and partially applied initial actions are outside this probe',
            'Initial setup used max_retries=1 and failed the one-recovery-call assertion; the unchanged source requires 2 for one retry',
        ])
    with args.output.open('x', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write('\n')
    print(json.dumps({'cases': len(cases), 'controls_passed': True,
                      'unchecked_error_status_cases': [indexed[r, 'none', 'error_status']
                                                       for r in ('retry', 'alternative')]}))


if __name__ == '__main__':
    main()
