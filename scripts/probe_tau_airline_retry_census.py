"""Direct native cancellation retries; no models, MCP or external service."""
import hashlib
import importlib.metadata
import json
from decimal import Decimal
from pathlib import Path
import socket
import sys

from tau_airline_compensation_fixture import load, ROOT, sha


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def measure(reservation):
    amounts = [Decimal(str(p['amount'])) for p in reservation['payment_history']]
    net = sum(amounts, Decimal(0))
    return {'contract_met': reservation['status'] == 'cancelled' and net == 0,
            'entries': len(amounts), 'net': str(net),
            'positive': str(sum((a for a in amounts if a > 0), Decimal(0))),
            'negative': str(sum((a for a in amounts if a < 0), Decimal(0)))}


def main():
    connections = []
    def guard(event, args):
        if event == 'socket.connect':
            connections.append(str(args[1]))
            raise PermissionError('Offline native cancellation census')
    sys.addaudithook(guard)
    out = Path('results/probes/tau-airline-retry-census-v1')
    out.mkdir(parents=True, exist_ok=False)
    summary_path = Path('research/evidence/tau_airline_retry_census_v1.json')
    assert not summary_path.exists()
    tools, _, metadata = load('single_card')
    from tau2.domains.airline.data_model import get_db
    tools.db = get_db()
    initial_db = tools.db.model_dump(mode='json')
    initial_hash = digest(initial_db)
    data_path = ROOT/'data/tau2/domains/airline/db.json'
    manifest = json.loads(Path('research/evidence/tau2_source_manifest.json').read_bytes())
    assert sha(data_path) == manifest['data/tau2/domains/airline/db.json']
    assert len(initial_db['reservations']) == 2000
    counts = {'reservations': 0, 'native_cancel_calls': 0, 'native_read_calls': 0,
              'imposed_ack_errors': 0, 'read_policy_equal_to_single': 0,
              'blind_policy_equal_to_single': 0, 'all_post_cancel_contracts_met': 0}
    raw = out/'records.jsonl'
    with raw.open('x', encoding='utf-8', newline='\n') as stream:
        for rid in sorted(initial_db['reservations']):
            original_model = tools.db.reservations[rid].model_copy(deep=True)
            before = original_model.model_dump(mode='json')
            row = {'reservation_id': rid, 'before': before, 'policies': {}}
            for policy, retries in [('single', 1), ('blind_three', 3), ('read_before_retry', 1)]:
                tools.db.reservations[rid] = original_model.model_copy(deep=True)
                steps = []
                for _ in range(retries):
                    payload = tools.cancel_reservation(rid).model_dump(mode='json')
                    counts['native_cancel_calls'] += 1
                    step = {'native_payload': payload, 'state': tools.db.reservations[rid].model_dump(mode='json'),
                            'measurement': measure(payload), 'imposed_ack_error': None}
                    if policy != 'single':
                        try:
                            raise RuntimeError('Constructed acknowledgement error after native cancellation')
                        except RuntimeError as exc:
                            step['imposed_ack_error'] = {'type': type(exc).__name__, 'message': str(exc)}
                            counts['imposed_ack_errors'] += 1
                    steps.append(step)
                read_payload = None
                stop = None
                if policy == 'read_before_retry':
                    read_payload = tools.get_reservation_details(rid).model_dump(mode='json')
                    counts['native_read_calls'] += 1
                    stop = measure(read_payload)['contract_met']
                final = tools.db.reservations[rid].model_dump(mode='json')
                row['policies'][policy] = {'steps': steps, 'read_payload': read_payload,
                                           'stopped_on_contract': stop, 'final': final,
                                           'final_sha256': digest(final)}
            single = row['policies']['single']['final']
            counts['read_policy_equal_to_single'] += row['policies']['read_before_retry']['final'] == single
            counts['blind_policy_equal_to_single'] += row['policies']['blind_three']['final'] == single
            counts['all_post_cancel_contracts_met'] += all(s['measurement']['contract_met'] for p in row['policies'].values() for s in p['steps'])
            counts['reservations'] += 1
            tools.db.reservations[rid] = original_model
            stream.write(json.dumps(row, separators=(',', ':'))+'\n')
    restored_hash = digest(tools.db.model_dump(mode='json'))
    assert restored_hash == initial_hash
    report = {'study': 'native cancellation direct-call census, not agent benchmark',
              'metadata': metadata, 'protocol_sha256': sha(Path('research/native_airline_retry_protocol.md')),
              'script_sha256': sha(Path(__file__)), 'fixture_loader_sha256': sha(Path('scripts/tau_airline_compensation_fixture.py')),
              'database_sha256': sha(data_path), 'counts': counts,
              'raw': str(raw).replace('\\', '/'), 'raw_sha256': sha(raw), 'raw_bytes': raw.stat().st_size,
              'initial_model_database_sha256': initial_hash, 'restored_model_database_sha256': restored_hash,
              'external_connection_attempts': connections, 'model_calls': 0,
              'python': sys.version, 'executable': sys.executable,
              'packages': {d.metadata['Name']: d.version for d in importlib.metadata.distributions()}}
    with summary_path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps(counts))


if __name__ == '__main__':
    main()
