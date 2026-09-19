"""Recompute the complete native retry census without importing its tool code."""
import copy
import hashlib
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
import zipfile


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def main():
    report_path = Path('research/evidence/tau_airline_retry_census_v1.json')
    report = json.loads(report_path.read_bytes())
    raw = Path(report['raw'])
    assert sha(raw) == report['raw_sha256'] and raw.stat().st_size == report['raw_bytes']
    for key, name in [('script_sha256', 'scripts/probe_tau_airline_retry_census.py'),
                      ('fixture_loader_sha256', 'scripts/tau_airline_compensation_fixture.py'),
                      ('protocol_sha256', 'research/native_airline_retry_protocol.md')]:
        assert sha(Path(name)) == report[key]
    db_path = Path('results/third_party/tau2-bench/data/tau2/domains/airline/db.json')
    assert sha(db_path) == report['database_sha256']
    source = json.loads(db_path.read_bytes())['reservations']
    seen = set()
    cancels = reads = errors = 0
    net_checks = 0
    count_patterns = Counter()
    payment_types = Counter()
    for line in raw.open(encoding='utf-8'):
        row = json.loads(line)
        rid = row['reservation_id']
        assert rid not in seen and rid in source
        seen.add(rid)
        initial = copy.deepcopy(source[rid])
        assert 'status' not in initial
        initial['status'] = None
        assert initial == row['before']
        assert len(initial['payment_history']) == 1
        payment_types[initial['payment_history'][0]['payment_id'].rsplit('_', 1)[0]] += 1
        assert set(row['policies']) == {'single', 'blind_three', 'read_before_retry'}
        for policy, steps in [('single', 1), ('blind_three', 3), ('read_before_retry', 1)]:
            result = row['policies'][policy]
            assert len(result['steps']) == steps
            expected = copy.deepcopy(initial)
            for observation in result['steps']:
                refunds = [{'payment_id': p['payment_id'], 'amount': -p['amount']}
                           for p in expected['payment_history']]
                expected['payment_history'].extend(refunds)
                expected['status'] = 'cancelled'
                assert observation['native_payload'] == expected == observation['state']
                amounts = [Decimal(str(p['amount'])) for p in expected['payment_history']]
                net = sum(amounts, Decimal(0))
                measured = observation['measurement']
                assert net == Decimal(measured['net']) == 0
                assert measured['entries'] == len(amounts)
                assert measured['contract_met'] is True
                assert Decimal(measured['positive']) == sum((v for v in amounts if v > 0), Decimal(0))
                assert Decimal(measured['negative']) == sum((v for v in amounts if v < 0), Decimal(0))
                if policy == 'single':
                    assert observation['imposed_ack_error'] is None
                else:
                    assert observation['imposed_ack_error'] == {
                        'type': 'RuntimeError',
                        'message': 'Constructed acknowledgement error after native cancellation'}
                    errors += 1
                cancels += 1
                net_checks += 1
            assert result['final'] == expected and result['final_sha256'] == digest(expected)
            if policy == 'read_before_retry':
                assert result['read_payload'] == expected and result['stopped_on_contract'] is True
                reads += 1
            else:
                assert result['read_payload'] is None and result['stopped_on_contract'] is None
        p = row['policies']
        assert p['single']['final'] == p['read_before_retry']['final']
        assert p['single']['final'] != p['blind_three']['final']
        count_patterns[tuple(len(s['state']['payment_history']) for s in p['blind_three']['steps'])] += 1
    assert seen == set(source) and len(seen) == 2000
    assert (cancels, reads, errors) == (10000, 2000, 8000)
    assert report['counts'] == {'reservations': 2000, 'native_cancel_calls': cancels,
        'native_read_calls': reads, 'imposed_ack_errors': errors,
        'read_policy_equal_to_single': 2000, 'blind_policy_equal_to_single': 0,
        'all_post_cancel_contracts_met': 2000}
    assert report['initial_model_database_sha256'] == report['restored_model_database_sha256']
    assert report['external_connection_attempts'] == [] and report['model_calls'] == 0
    validation_path = Path('research/evidence/tau_airline_retry_census_validation_v2.json')
    validation = {'valid': True, 'validator_sha256': sha(Path(__file__)),
        'report_sha256': sha(report_path), 'raw_sha256': sha(raw),
        'population': len(seen), 'states_and_nets_recomputed': net_checks,
        'ledger_entry_patterns': {str(k): v for k, v in count_patterns.items()},
        'initial_payment_type_counts': dict(payment_types),
        'interpretation': 'Finite native input census; no agent tasks, external payments, MCP, stale reads or concurrency.'}
    with validation_path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(validation, stream, indent=2)
        stream.write('\n')
    paths = [raw, report_path, validation_path, Path(__file__).resolve().relative_to(Path.cwd()),
             Path('scripts/probe_tau_airline_retry_census.py'),
             Path('scripts/tau_airline_compensation_fixture.py'),
             Path('research/native_airline_retry_protocol.md'),
             Path('results/probes/tau-airline-retry-census-v1/validator_packaging_attempt_v1.py'),
             Path('research/evidence/tau_airline_retry_census_validation_v1.json')]
    archive = Path('results/remote/tau-airline-retry-census-v2-evidence.zip')
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as z:
        for path in paths:
            z.write(path, path.as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert all(hashlib.sha256(z.read(p.as_posix())).hexdigest() == sha(p) for p in paths)
    receipt = {'archive': archive.as_posix(), 'bytes': archive.stat().st_size,
               'sha256': sha(archive), 'files': {p.as_posix(): sha(p) for p in paths},
               'dependency': 'Pinned tau2 source/database and fixture bytes from the native-airline study; not vendored in this archive.',
               'packaging_amendment': 'Initial validation passed; post-packaging verification failed because __file__ was absolute and ZIP removed the Windows drive prefix. V2 uses a repository-relative path. Same raw run; initial validator and validation retained.'}
    with Path('research/evidence/tau_airline_retry_census_receipt_v2.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'validation': validation, 'archive_bytes': archive.stat().st_size, 'archive_sha256': sha(archive)}))


if __name__ == '__main__':
    main()
