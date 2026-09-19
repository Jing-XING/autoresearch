"""Check raw state/WAL consistency and construct a scoped cross-implementation table."""
import hashlib
import json
from pathlib import Path


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    source = Path('research/evidence/independent_compensation_probe_v2.json')
    prior = Path('research/evidence/rac_real_mcp_probe_v1.json')
    result, rac = [json.loads(p.read_bytes()) for p in (source, prior)]
    assert result['script_sha256'] == sha(Path('scripts/probe_independent_compensation.py'))
    assert result['fixture_script_sha256'] == sha(Path('scripts/rac_mcp_fixture_server.py'))
    assert result['fixture_script_sha256'] in rac['scripts_sha256'].values()
    assert len(result['sagallm_cases']) == 6 and len(result['agent_saga_mcp_cases']) == 8
    assert not result['parent_external_connection_attempts'] and result['model_calls'] == 0
    comparisons, raw_hashes = [], {}
    for row in result['agent_saga_mcp_cases']:
        wal = Path(row['wal_file'])
        assert sha(wal) == row['wal_sha256']
        state_path = wal.with_name(wal.name.replace('.wal.jsonl', '.json'))
        assert sha(state_path) == row['state_sha256']
        state = json.loads(state_path.read_bytes())
        assert state == row['fixture_state']
        assert [c['name'] for c in state['calls']] == ['book','cancel']
        events = [json.loads(line) for line in wal.read_text(encoding='utf-8').splitlines()]
        assert events[0]['event'] == 'SAGA_START'
        assert events[-1]['event'] == 'SAGA_ABORTED'
        terminal = next(e for e in events if e['event'] == 'ROLLBACK_END')
        assert terminal['clean'] == row['rollback_report']['clean'] == events[-1]['clean']
        assert terminal['compensated'] == row['rollback_report']['rolled_back']
        assert len(row['states_before_rollback']) == len(row['states_after_rollback']) == 1
        if row['states_before_rollback'][0] == 'UNKNOWN':
            assert row['forward_exception'] is not None
            assert any(e['event'] == 'STEP_UNKNOWN' for e in events)
        if row['states_after_rollback'][0] == 'COMPENSATION_FAILED':
            assert not terminal['clean'] and terminal['failed'] == 1
            assert any(e['event'] == 'COMPENSATION_FAILED' for e in events)
        if row['route'] == 'rollback':
            original = next(r for r in rac['cases'] if r['route'] == 'rollback'
                            and r['behavior'] == row['behavior'] and not r['legacy_raise_control'])
            assert original['fixture_state'] == state
            comparisons.append(dict(behavior=row['behavior'], fixture_active=state['active'],
                rac_default_reported_success=original['rollback_reported_success'],
                rac_status=original['record_status'], agent_saga_clean=row['rollback_report']['clean'],
                agent_saga_status=row['states_after_rollback'][0]))
        raw_hashes[str(wal)] = sha(wal)
        raw_hashes[str(state_path)] = sha(state_path)
    for row in result['sagallm_cases']:
        assert row['raised_to_caller'] is None
        expected = ['booking:run','downstream:run','booking:rollback'] if row['route'] == 'rollback' else ['booking:run']
        assert row['fixture_state']['events'] == expected
    report = dict(purpose=__doc__, input_sha256={str(p):sha(p) for p in (source,prior)},
                  raw_sha256=raw_hashes, actual_sdk_rollback_comparisons=comparisons,
                  checked_agent_saga_cases=8, checked_sagallm_cases=6,
                  limits='Identical constructed MCP fixture and behavior controls; differing library stacks and supplied declaration mechanisms. No task-level superiority or automatic-discovery comparison.')
    out = Path('research/evidence/independent_compensation_validation_v1.json')
    with out.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(report,stream,indent=2)
        stream.write('\n')
    print(json.dumps(comparisons))


if __name__ == '__main__':
    main()
