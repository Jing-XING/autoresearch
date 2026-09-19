"""Pinned native retail composition census on public synthetic database state.

No model, MCP transport, real payment service, or benchmark task scoring.
"""
import argparse
from collections import Counter, defaultdict
from decimal import Decimal
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def signed_balances(history):
    balances = defaultdict(lambda: Decimal(0))
    for entry in history:
        kind = entry['transaction_type']
        if kind not in ('payment', 'refund'): raise ValueError('Unknown transaction type')
        amount = Decimal(str(entry['amount']))
        if amount < 0 or not amount.is_finite(): raise ValueError('Invalid unsigned amount')
        balances[entry['payment_method_id']] += amount * (1 if kind == 'payment' else -1)
    return {key: str(value) for key, value in sorted(balances.items())}


def measure(order, methods, expected_gift):
    ledger = signed_balances(order['payment_history'])
    actual_gift = {k: str(v['balance']) for k, v in sorted(methods.items()) if v['source'] == 'gift_card'}
    zero = all(Decimal(v) == 0 for v in ledger.values())
    gift_ok = set(actual_gift) == set(expected_gift) and all(
        abs(Decimal(actual_gift[k]) - Decimal(v)) <= Decimal('0.000001') for k, v in expected_gift.items())
    return dict(status=order['status'], signed_net_by_method=ledger,
                signed_net_total=str(sum(map(Decimal, ledger.values()), Decimal(0))),
                ledger_entries=len(order['payment_history']), gift_balances=actual_gift,
                cancelled=order['status'] == 'cancelled', per_method_net_zero=zero,
                expected_cancelled_gift_balances_met=gift_ok,
                cancellation_contract_met=order['status'] == 'cancelled' and zero and gift_ok)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    upstream = root/'tau'
    manifest = json.loads((root/'research/evidence/tau2_source_manifest.json').read_bytes())
    assert digest(manifest) == 'd07cc342f43894f866d1fd151fdd1ed996976cb194299e2d87913bc5bc8ee349'
    verified = {p: h for p, h in manifest.items() if p.startswith('src/') or p in (
        'data/tau2/domains/retail/db.json', 'data/tau2/domains/retail/policy.md')}
    for rel, expected in verified.items():
        assert sha(upstream/rel) == expected, rel
    os.environ.update(PYTHON_DOTENV_DISABLED='1', LITELLM_LOCAL_MODEL_COST_MAP='True',
                      TAU2_DATA_DIR=str(upstream/'data'))
    connections = []
    def offline(event, values):
        if event == 'socket.connect':
            connections.append(str(values[1])); raise PermissionError('Offline native retail diagnostic')
    sys.addaudithook(offline)
    sys.path.insert(0, str(upstream/'src'))
    from loguru import logger
    logger.remove()
    import tau2
    assert Path(tau2.__file__).resolve().is_relative_to(upstream.resolve())
    from tau2.domains.retail.data_model import RetailDB
    from tau2.domains.retail.tools import RetailTools
    tools = RetailTools(RetailDB.load(upstream/'data/tau2/domains/retail/db.json'))
    initial = tools.db.model_dump(mode='json')
    args.output.mkdir(parents=True, exist_ok=False)
    counts = Counter(); excluded = []; selected = []; by_type = Counter()
    for oid, order in sorted(initial['orders'].items()):
        history = order['payment_history']
        reason = None
        if order['status'] != 'pending': reason = 'not_pending'
        elif len(history) != 1 or history[0]['transaction_type'] != 'payment': reason = 'not_single_initial_payment'
        elif history[0]['amount'] <= 0: reason = 'nonpositive_initial_amount'
        elif history[0]['payment_method_id'] not in initial['users'][order['user_id']]['payment_methods']: reason = 'unknown_original_payment'
        if reason:
            excluded.append(dict(order_id=oid, reason=reason)); continue
        methods = initial['users'][order['user_id']]['payment_methods']
        old = history[0]['payment_method_id']; amount = Decimal(str(history[0]['amount']))
        alternatives = []
        for mid, method in sorted(methods.items()):
            if mid == old: continue
            if method['source'] == 'gift_card' and Decimal(str(method['balance'])) < amount: continue
            alternatives.append(mid)
        selected.append(dict(order_id=oid, alternatives=alternatives))
    selection = dict(total_orders=len(initial['orders']), selected=selected, excluded=excluded)
    (args.output/'selection.json').write_text(json.dumps(selection, indent=2)+'\n', encoding='utf8')
    with (args.output/'records.jsonl').open('x', encoding='utf8') as stream:
        for selection_row in selected:
            oid = selection_row['order_id']; uid = initial['orders'][oid]['user_id']
            original_order = tools.db.orders[oid].model_copy(deep=True)
            original_user = tools.db.users[uid].model_copy(deep=True)
            before = dict(order=original_order.model_dump(mode='json'),
                          payment_methods=original_user.model_dump(mode='json')['payment_methods'])
            payment = before['order']['payment_history'][0]
            old = payment['payment_method_id']; amount = Decimal(str(payment['amount']))
            expected_gift = {k: str(Decimal(str(v['balance'])) + (amount if k == old else 0))
                             for k, v in before['payment_methods'].items() if v['source'] == 'gift_card'}
            for new in [None] + selection_row['alternatives']:
                tools.db.orders[oid] = original_order.model_copy(deep=True)
                tools.db.users[uid] = original_user.model_copy(deep=True)
                kind = 'cancel_only' if new is None else 'change_then_cancel'
                steps = []; calls = []
                if new is not None: calls.append(('modify_pending_order_payment', dict(order_id=oid, payment_method_id=new)))
                calls.append(('cancel_pending_order', dict(order_id=oid, reason='no longer needed')))
                for name, kwargs in calls:
                    result = error = None
                    try: result = getattr(tools, name)(**kwargs).model_dump(mode='json')
                    except Exception as exc: error = dict(type=type(exc).__name__, message=str(exc))
                    counts['native_calls'] += 1
                    state = dict(order=tools.db.orders[oid].model_dump(mode='json'),
                                 payment_methods=tools.db.users[uid].model_dump(mode='json')['payment_methods'])
                    observation = measure(state['order'], state['payment_methods'], expected_gift)
                    steps.append(dict(tool=name, arguments=kwargs, result=result, error=error, state=state, measurement=observation))
                    if error:
                        counts['native_exceptions'] += 1
                        break
                counts[kind] += 1
                counts[kind+'_contract_met'] += steps[-1]['measurement']['cancellation_contract_met']
                counts[kind+'_normal_return'] += all(s['error'] is None for s in steps)
                counts[kind+'_cancelled'] += steps[-1]['measurement']['cancelled']
                if new is not None:
                    by_type[before['payment_methods'][old]['source']+'->'+before['payment_methods'][new]['source']] += 1
                row = dict(order_id=oid, user_id=uid, kind=kind, old_payment_method=old,
                           new_payment_method=new, before=before, expected_cancelled_gift_balances=expected_gift, steps=steps)
                stream.write(json.dumps(row, separators=(',', ':'))+'\n'); stream.flush()
            tools.db.orders[oid] = original_order
            tools.db.users[uid] = original_user
    final_hash = digest(tools.db.model_dump(mode='json'))
    assert final_hash == digest(initial)
    report = dict(scope='Direct native composition diagnostic on public synthetic state; no agents, external payments, MCP transport or benchmark scores.',
                  tau_revision='b7ea9074c1cba482b30687fecdb5c8425fd6f619', source_files_verified=len(verified),
                  counts=dict(counts), payment_type_pairs=dict(by_type),
                  initial_orders=len(initial['orders']), eligible_orders=len(selected),
                  eligible_orders_with_alternatives=sum(bool(r['alternatives']) for r in selected),
                  excluded_by_reason=dict(Counter(r['reason'] for r in excluded)),
                  database_restored=True, initial_database_sha256=digest(initial), restored_database_sha256=final_hash,
                  python=sys.version, packages={p: importlib.metadata.version(p) for p in ('pydantic','loguru','litellm')},
                  script_sha256=sha(Path(__file__)), protocol_sha256=sha(root/'research/native_retail_composition_protocol_v1.md'),
                  database_sha256=sha(upstream/'data/tau2/domains/retail/db.json'),
                  policy_sha256=sha(upstream/'data/tau2/domains/retail/policy.md'),
                  records_sha256=sha(args.output/'records.jsonl'), selection_sha256=sha(args.output/'selection.json'),
                  model_calls=0, external_connection_attempts=connections)
    with (args.output/'summary.json').open('x', encoding='utf8') as f: json.dump(report, f, indent=2); f.write('\n')
    print(json.dumps(dict(counts=report['counts'], eligible_orders=report['eligible_orders'], payment_type_pairs=report['payment_type_pairs'])))
    if connections or counts['native_exceptions']: raise SystemExit(2)


if __name__ == '__main__': main()
