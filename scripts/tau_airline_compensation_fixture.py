"""Pinned native tau2 airline tools on an official unit-test database.

The two constructed profiles are diagnostic workflows, not official agent tasks.
No airline service, model provider, or external network is contacted.
"""
import ast
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys

ROOT = Path('results/third_party/tau2-bench').resolve()
FIXTURE = Path('results/third_party/tau2-airline-fixture/test_tools_airline.py')
FIXTURE_SHA = '3c2c621f7fae1117903ce84dc11abbbd0136118de51a297276422e70f263cc6d'
CANONICAL = 'd07cc342f43894f866d1fd151fdd1ed996976cb194299e2d87913bc5bc8ee349'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(profile):
    assert profile in ('single_card', 'two_leg_mixed')
    manifest = json.loads(Path('research/evidence/tau2_source_manifest.json').read_bytes())
    assert hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()).hexdigest() == CANONICAL
    source_hashes = {k: v for k, v in manifest.items() if k.startswith('src/')}
    for rel, expected in source_hashes.items():
        assert sha(ROOT/rel) == expected, rel
    assert sha(FIXTURE) == FIXTURE_SHA
    os.environ.update(PYTHON_DOTENV_DISABLED='1', LITELLM_LOCAL_MODEL_COST_MAP='True',
                      TAU2_DATA_DIR=str(ROOT/'data'))
    sys.path.insert(0, str(ROOT/'src'))
    from loguru import logger
    logger.remove()
    import tau2
    assert Path(tau2.__file__).resolve().is_relative_to(ROOT)
    from tau2.domains.airline.data_model import FlightDB, FlightInfo, Passenger, Payment
    from tau2.domains.airline.tools import AirlineTools
    from tau2.data_model.message import ToolCall
    namespace = dict(FlightDB=FlightDB, FlightInfo=FlightInfo, Passenger=Passenger, Payment=Payment, ToolCall=ToolCall)
    nodes = []
    for node in ast.parse(FIXTURE.read_bytes()).body:
        if isinstance(node, ast.FunctionDef) and node.name in ('airline_db', 'reservation_call'):
            node.decorator_list = []  # Only bypass pytest fixture registration.
            nodes.append(node)
    assert len(nodes) == 2
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(FIXTURE), 'exec'), namespace)
    db = namespace['airline_db']()
    booking = namespace['reservation_call']().model_dump(mode='json')['arguments']
    if profile == 'two_leg_mixed':
        booking['destination'] = 'LAX'
        booking['flights'].append({'flight_number': 'HAT002', 'date': '2024-05-16'})
        booking['payment_methods'] = [{'payment_id': 'certificate_4856383', 'amount': 100},
                                      {'payment_id': 'credit_card_4421486', 'amount': 144}]
    tools = AirlineTools(db)
    metadata = {'tau_commit': 'b7ea9074c1cba482b30687fecdb5c8425fd6f619',
                'tau_canonical_manifest': CANONICAL, 'source_files_verified': len(source_hashes),
                'fixture_sha256': FIXTURE_SHA, 'profile': profile,
                'profile_selection': 'official single-flight card fixture; declared two-leg mixed-payment extension',
                'packages': {n: importlib.metadata.version(n) for n in ('tau2', 'pydantic', 'loguru', 'mcp', 'litellm')}}
    return tools, booking, metadata


def observe(before, after, reservation_id, booking):
    reservation = after['reservations'][reservation_id]
    payments = reservation['payment_history']
    net = sum(p['amount'] for p in payments)
    seat_rows = []
    for flight in booking['flights']:
        number, date, cabin = flight['flight_number'], flight['date'], booking['cabin']
        seat_rows.append({'flight_number': number, 'date': date,
                         'before': before['flights'][number]['dates'][date]['available_seats'][cabin],
                         'after': after['flights'][number]['dates'][date]['available_seats'][cabin]})
    user_id = booking['user_id']
    return {'reservation_status': reservation.get('status'), 'payment_ledger_net': net,
            'payment_ledger_entries': len(payments),
            'cancellation_contract_met': reservation.get('status') == 'cancelled' and net == 0,
            'seat_counts': seat_rows, 'seat_inventory_restored': all(r['before'] == r['after'] for r in seat_rows),
            'payment_instruments_restored': before['users'][user_id]['payment_methods'] == after['users'][user_id]['payment_methods'],
            'full_database_restored': before == after,
            'existing_reservations_unchanged': all(after['reservations'][k] == v for k, v in before['reservations'].items()),
            'oracle_scope': 'cancelled status plus zero net reservation payment ledger; inventory/payment-instrument restoration reported separately, not required by the declared cancellation contract'}


if __name__ == '__main__':
    rows = []
    for profile in ('single_card', 'two_leg_mixed'):
        tools, booking, metadata = load(profile)
        before = tools.db.model_dump(mode='json')
        result = tools.book_reservation(**booking)
        reservation_id = result.reservation_id
        booked = tools.db.model_dump(mode='json')
        tools.cancel_reservation(reservation_id)
        after = tools.db.model_dump(mode='json')
        oracle = observe(before, after, reservation_id, booking)
        assert oracle['cancellation_contract_met'] and not oracle['seat_inventory_restored']
        rows.append({'metadata': metadata, 'booking': booking, 'reservation_id': reservation_id,
                     'before': before, 'booked': booked, 'after': after, 'oracle': oracle})
    out = Path('research/evidence/tau_airline_compensation_preflight_v1.json')
    with out.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump({'script_sha256': sha(Path(__file__)), 'cases': rows, 'model_calls': 0}, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'profiles': len(rows), 'native_booking_and_cancellation_completed': True}))
