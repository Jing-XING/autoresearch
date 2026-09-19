"""Fixed, descriptive audit of public retail tool-call/result observations."""
import argparse
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path


def sha(b): return hashlib.sha256(b).hexdigest()


def ledger(order):
    history = order.get('payment_history')
    if not isinstance(history, list) or not history:
        return {'scorable': False, 'reason': 'missing_or_empty_history'}
    net = defaultdict(lambda: Decimal(0))
    for entry in history:
        try:
            kind = entry['transaction_type']; method = entry['payment_method_id']
            amount = Decimal(str(entry['amount']))
            if kind not in ('payment', 'refund') or not isinstance(method, str) or not amount.is_finite() or amount < 0:
                raise ValueError('invalid entry')
            net[method] += amount * (1 if kind == 'payment' else -1)
        except (KeyError, TypeError, ValueError, InvalidOperation):
            return {'scorable': False, 'reason': 'invalid_ledger_entry'}
    return {'scorable': True, 'entries': len(history),
            'net_by_method': {k: str(v) for k, v in sorted(net.items())},
            'all_methods_zero': all(v == 0 for v in net.values())}


def extract(simulation):
    messages = simulation['messages']; calls = []; results = defaultdict(list)
    for mi, message in enumerate(messages):
        if message['role'] == 'assistant':
            for ci, call in enumerate(message.get('tool_calls') or []):
                if call.get('requestor', 'assistant') == 'assistant':
                    calls.append((mi, ci, call))
        if message['role'] == 'tool' and message.get('requestor', 'assistant') == 'assistant':
            results[message['id']].append((mi, message))
    ids = Counter(c['id'] for _, _, c in calls)
    selected = []
    for mi, ci, call in calls:
        if call['name'] not in ('modify_pending_order_payment', 'cancel_pending_order'):
            continue
        matches = results[call['id']]
        row = dict(message_index=mi, call_index=ci, call=call,
                   result_matches=[{'message_index': i, 'message': m} for i, m in matches])
        if ids[call['id']] != 1: row['association'] = 'reused_call_id'
        elif len(matches) != 1: row['association'] = 'missing_result' if not matches else 'multiple_results'
        elif matches[0][0] <= mi: row['association'] = 'result_not_after_call'
        else: row['association'] = 'unique_following_result'
        row['order'] = None
        if row['association'] == 'unique_following_result':
            try:
                value = json.loads(matches[0][1]['content'])
                if isinstance(value, dict) and value.get('order_id') == call['arguments'].get('order_id'):
                    row['order'] = value
            except (TypeError, ValueError): pass
        row['normal_order_return'] = (row['order'] is not None and
            row['result_matches'][0]['message'].get('error') is False)
        if call['name'] == 'cancel_pending_order':
            row['earlier_change_indices'] = [i for i, prior in enumerate(selected)
                if prior['call']['name'] == 'modify_pending_order_payment'
                and prior['call']['arguments'].get('order_id') == call['arguments'].get('order_id')]
            row['qualifying_change_indices'] = [i for i in row['earlier_change_indices']
                if selected[i]['normal_order_return']
                and selected[i]['order'].get('status') == 'pending'
                and selected[i]['result_matches'][0]['message_index'] < mi
                and row['normal_order_return'] and row['order'].get('status') == 'cancelled']
            row['unordered_same_message_changes'] = [c for m, _, c in calls if m == mi
                and c['name'] == 'modify_pending_order_payment'
                and c['arguments'].get('order_id') == call['arguments'].get('order_id')]
            row['ledger'] = ledger(row['order']) if row['order'] is not None and row['order'].get('status') == 'cancelled' else {'scorable': False, 'reason': 'no_matching_cancelled_order'}
        selected.append(row)
    return selected


def summarize(records):
    counts = Counter(simulations=len(records)); tasks = defaultdict(set)
    for rec in records:
        for row in rec['selected_calls']:
            name = row['call']['name']; counts[name] += 1
            counts['association_' + row['association']] += 1
            if name != 'cancel_pending_order': continue
            for key, test in [
                ('cancel_with_earlier_change', bool(row['earlier_change_indices'])),
                ('qualifying_composition', bool(row['qualifying_change_indices'])),
                ('cancel_with_same_message_change', bool(row['unordered_same_message_changes'])),
                ('scored_cancel_payload', row['ledger']['scorable']),
                ('nonzero_cancel_payload', row['ledger']['scorable'] and not row['ledger']['all_methods_zero'])]:
                if test: counts[key] += 1; tasks[key].add(rec['task_id'])
    for key in ['modify_pending_order_payment', 'cancel_pending_order', 'cancel_with_earlier_change',
                'qualifying_composition', 'cancel_with_same_message_change', 'scored_cancel_payload', 'nonzero_cancel_payload']:
        counts[key] += 0
    return dict(counts=dict(counts), distinct_tasks={k: len(v) for k, v in sorted(tasks.items())})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--output', type=Path, required=True)
    args=parser.parse_args(); root=args.root
    registration_path=root/'research/evidence/retail_archive_composition_registration_v1.json'
    reg=json.loads(registration_path.read_bytes())
    for rel, expected in reg['analysis_inputs'].items():
        assert sha((root/rel).read_bytes()) == expected, rel
    base=root/'results/third_party/tau2-bench/data/tau2/results/final'
    assert {p.name for p in base.glob('*_retail_*.json')} == set(reg['archives'])
    output=[]; all_records=[]; duplicate_index=defaultdict(list)
    for name, expected in sorted(reg['archives'].items()):
        raw=(base/name).read_bytes();assert sha(raw)==expected['sha256'] and len(raw)==expected['bytes']
        data=json.loads(raw); records=[];seen=set();pairs=set()
        assert len(data['tasks'])==114 and len(data['simulations'])==456
        for si, sim in enumerate(data['simulations']):
            pair=(sim['task_id'],sim['trial'])
            assert sim['id'] not in seen and pair not in pairs
            seen.add(sim['id']);pairs.add(pair)
            canonical=sha(json.dumps(sim,sort_keys=True,separators=(',',':')).encode())
            duplicate_index[canonical].append([name,si,sim['id']])
            records.append(dict(source=name,simulation_index=si,simulation_id=sim['id'],
                task_id=sim['task_id'],trial=sim['trial'],seed=sim['seed'],
                original_reward=sim['reward_info']['reward'],selected_calls=extract(sim)))
        assert pairs == {(t['id'],trial) for t in data['tasks'] for trial in range(4)}
        output.append(dict(file=name,sha256=sha(raw),bytes=len(raw),recorded_execution_commit=data['info']['git_commit'],
                           agent=data['info']['agent_info'],summary=summarize(records)))
        all_records.extend(records)
    result=dict(scope='Archived returned payloads only; no independent persisted state, replay, reward revision or prevalence outside these fixed files.',
                registration_sha256=sha(registration_path.read_bytes()),files=output,
                summary=summarize(all_records),canonical_duplicate_groups=[v for v in duplicate_index.values() if len(v)>1],records=all_records)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as f: json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:result[k] for k in ('summary','canonical_duplicate_groups')}))


if __name__=='__main__':main()
