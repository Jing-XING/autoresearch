"""Recompute native domain effects from preserved database snapshots."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    evidence = Path('research/evidence/tau_airline_compensation_probe_v1.json')
    report = json.loads(evidence.read_bytes())
    keys = {(r['profile'], r['fault'], r['condition']) for r in report['cases']}
    expected = {(p, m, c) for p in ('single_card', 'two_leg_mixed')
                for m in ('normal', 'native_error_before_effect', 'shadow_only', 'error_after_effect')
                for c in ('rac_default', 'rac_raise_control', 'agent_saga')}
    expected.add(('single_card', 'normal', 'rac_unadapted_mapper'))
    assert keys == expected and len(report['cases']) == len(expected)
    for path, digest in report['scripts_sha256'].items():
        assert sha(Path(path)) == digest
    preflight = Path('research/evidence/tau_airline_compensation_preflight_v1.json')
    assert sha(preflight) == report['preflight_sha256']
    preflight_cases = {r['metadata']['profile']: r for r in json.loads(preflight.read_bytes())['cases']}
    raw, groups, findings = {}, defaultdict(list), []
    wal_count = 0
    for row in report['cases']:
        path = Path(row['raw_state_file'])
        assert path.resolve().is_relative_to(Path('results/probes/tau-airline-mcp').resolve())
        assert sha(path) == row['raw_state_sha256']
        state = json.loads(path.read_bytes())
        profile, mode, condition = row['profile'], row['fault'], row['condition']
        rid = row['reservation_id']
        fixture = preflight_cases[profile]
        assert state['before'] == fixture['before'] and state['booking'] == fixture['booking']
        reservation = state['current']['reservations'][rid]
        assert set(state['current']['reservations']) - set(state['before']['reservations']) == {rid}
        assert all(state['current']['reservations'][k] == v for k, v in state['before']['reservations'].items())
        refunded = reservation.get('status') == 'cancelled' and sum(p['amount'] for p in reservation['payment_history']) == 0
        assert refunded == row['oracle']['cancellation_contract_met']
        assert state['current'] != state['before'] and row['oracle']['full_database_restored'] is False
        for flight in state['booking']['flights']:
            fn, date, cabin = flight['flight_number'], flight['date'], state['booking']['cabin']
            assert state['current']['flights'][fn]['dates'][date]['available_seats'][cabin] == state['before']['flights'][fn]['dates'][date]['available_seats'][cabin] - 1
        if 'wal_file' in row:
            wal_path = Path(row['wal_file'])
            assert sha(wal_path) == row['wal_sha256']
            records = [json.loads(line) for line in wal_path.read_text(encoding='utf-8').splitlines() if line.strip()]
            assert records
            wal_count += 1
        raw[(profile, mode, condition)] = state
        if condition != 'rac_unadapted_mapper':
            assert len(state['calls']) == 2
            groups[(profile, mode)].append(state['current'])
        findings.append({'profile': profile, 'fault': mode, 'condition': condition,
                         'cancellation_contract_met': refunded,
                         'framework_states': row['states_after'], 'framework_report': row['rollback_report']})
    assert all(len(values) == 3 and values[0] == values[1] == values[2] for values in groups.values())
    identical_responses = []
    for profile in ('single_card', 'two_leg_mixed'):
        for condition in ('rac_default', 'rac_raise_control', 'agent_saga'):
            normal = raw[(profile, 'normal', condition)]
            shadow = raw[(profile, 'shadow_only', condition)]
            response = normal['calls'][1]['native_result']
            assert response == shadow['calls'][1]['native_result']
            assert normal['current'] != shadow['current']
            identical_responses.append({'profile': profile, 'condition': condition,
                'returned_native_payload_sha256': hashlib.sha256(json.dumps(response, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
                'normal_and_shadow_response_equal': True, 'database_states_differ': True})
    result = {'evidence_sha256': sha(evidence), 'validated_cases': len(keys),
              'validated_wal_files': wal_count, 'cross_client_groups_with_identical_database_states': len(groups),
              'same_response_different_state_controls': identical_responses, 'case_findings': findings,
              'scope': 'independent arithmetic/state recomputation by the same research process; not independent human review',
              'script_sha256': sha(Path(__file__))}
    out = Path('research/evidence/tau_airline_compensation_validation_v1.json')
    with out.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k: result[k] for k in ['validated_cases', 'validated_wal_files', 'cross_client_groups_with_identical_database_states']}))


if __name__ == '__main__':
    main()
