"""Offline audit of native retail records, independent of the probe's oracle."""
from collections import Counter, defaultdict
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def sha(data): return hashlib.sha256(data).hexdigest()


def check(condition, message):
    if not condition: raise ValueError(message)


def ledger(history):
    value = defaultdict(lambda: Decimal(0))
    for p in history:
        check(p['transaction_type'] in ('payment','refund'), 'Unknown ledger sign')
        value[p['payment_method_id']] += Decimal(str(p['amount'])) * (1 if p['transaction_type']=='payment' else -1)
    return dict(value)


def main():
    archive = ROOT/'results/remote/native-retail-composition-v1-results.zip'
    check(sha(archive.read_bytes()) == '2586fb106a936211f5c6140f6da7271d91a40c4aabc663a17986df1a95397da5', 'Archive hash')
    with zipfile.ZipFile(archive) as z:
        check(len(z.namelist()) == len(set(z.namelist())) == 9, 'Archive members')
        members = {n:z.read(n) for n in z.namelist()}
    package = json.loads((ROOT/'research/evidence/native_retail_composition_package_v1.json').read_bytes())
    check(json.loads(members['deployment_manifest.json']) == package['manifest'], 'Deployment identity')
    for name, info in package['manifest']['files'].items():
        path = ROOT/('results/third_party/tau2-bench/'+name[4:] if name.startswith('tau/') else name)
        data = path.read_bytes()
        check(sha(data)==info['sha256'] and len(data)==info['bytes'], 'Local source mismatch '+name)
    report = json.loads(members['run/summary.json'])
    execution = json.loads(members['execution.json'])
    check([r['name'] for r in execution]==['tests','census'] and all(r['returncode']==0 and not r['timeout'] for r in execution), 'Remote failure')
    for name, field in [('run/records.jsonl','records_sha256'),('run/selection.json','selection_sha256')]:
        check(sha(members[name])==report[field], 'Raw hash')
    initial = json.loads((ROOT/'results/third_party/tau2-bench/data/tau2/domains/retail/db.json').read_bytes())
    check(sha((ROOT/'results/third_party/tau2-bench/data/tau2/domains/retail/db.json').read_bytes())==report['database_sha256'], 'Database hash')
    expected = set(); selected = []; excluded = []
    for oid, order in sorted(initial['orders'].items()):
        if order['status']!='pending':
            excluded.append(dict(order_id=oid,reason='not_pending'));continue
        h = order['payment_history']; methods = initial['users'][order['user_id']]['payment_methods']
        check(len(h)==1 and h[0]['transaction_type']=='payment' and h[0]['amount']>0 and h[0]['payment_method_id'] in methods, 'Unexpected pending input eligibility')
        old=h[0]['payment_method_id']; amount=Decimal(str(h[0]['amount']))
        alternatives=[k for k,v in sorted(methods.items()) if k!=old and (v['source']!='gift_card' or Decimal(str(v['balance']))>=amount)]
        selected.append(dict(order_id=oid,alternatives=alternatives))
        expected.add((oid,None))
        expected.update((oid,k) for k in alternatives)
    selection=json.loads(members['run/selection.json'])
    check(selection==dict(total_orders=1000,selected=selected,excluded=excluded), 'Selection census differs')
    rows=[json.loads(line) for line in members['run/records.jsonl'].splitlines()]
    check(len(rows)==len(expected) and {(r['order_id'],r['new_payment_method']) for r in rows}==expected, 'Missing, extra or repeated paths')
    counts=Counter(); types=Counter(); examples=[]
    for row in rows:
        oid,new=row['order_id'],row['new_payment_method'];before=row['before'];old=row['old_payment_method']
        original=initial['orders'][oid];methods=initial['users'][original['user_id']]['payment_methods']
        check(row['user_id']==original['user_id'] and before['payment_methods']==methods,'Initial user state differs')
        check(all(before['order'][k]==v for k,v in original.items()),'Initial order differs')
        amount=Decimal(str(original['payment_history'][0]['amount']))
        check(old==original['payment_history'][0]['payment_method_id'],'Original payment differs')
        expected_gift={k:Decimal(str(v['balance']))+(amount if k==old else 0) for k,v in methods.items() if v['source']=='gift_card'}
        check({k:Decimal(v) for k,v in row['expected_cancelled_gift_balances'].items()}==expected_gift,'Gift target differs')
        kind='cancel_only' if new is None else 'change_then_cancel'
        check(row['kind']==kind,'Path kind')
        check([s['tool'] for s in row['steps']]==(['cancel_pending_order'] if new is None else ['modify_pending_order_payment','cancel_pending_order']),'Call path')
        previous=before['order']['payment_history']
        for index,step in enumerate(row['steps']):
            check(step['error'] is None and step['result']==step['state']['order'],'Return/state mismatch')
            order=step['state']['order'];payments=step['state']['payment_methods'];observed=ledger(order['payment_history'])
            measure=step['measurement']
            check({k:Decimal(v) for k,v in measure['signed_net_by_method'].items()}==observed,'Reported ledger differs')
            check(Decimal(measure['signed_net_total'])==sum(observed.values(),Decimal(0)),'Net sum differs')
            check(measure['ledger_entries']==len(order['payment_history']),'Ledger count differs')
            check(all(order[k]==v for k,v in before['order'].items() if k not in ('status','payment_history','cancel_reason')),'Unrelated order mutation')
            if step['tool']=='modify_pending_order_payment':
                check(step['arguments']==dict(order_id=oid,payment_method_id=new),'Change arguments')
                check(order['status']=='pending' and observed=={old:Decimal(0),new:amount},'Change ledger contract')
                expected_history=previous+[dict(transaction_type='payment',amount=float(amount),payment_method_id=new),dict(transaction_type='refund',amount=float(amount),payment_method_id=old)]
            else:
                check(step['arguments']==dict(order_id=oid,reason='no longer needed'),'Cancel arguments')
                check(order['status']=='cancelled' and order['cancel_reason']=='no longer needed','Cancel status')
                expected_history=previous+[dict(transaction_type='refund',amount=p['amount'],payment_method_id=p['payment_method_id']) for p in previous]
                target={old:Decimal(0)} if new is None else {old:-2*amount,new:Decimal(0)}
                check(observed==target,'Unexpected final per-method ledger')
            check(order['payment_history']==expected_history,'Exact ledger entries differ')
            expected_methods=json.loads(json.dumps(methods))
            for mid,method in expected_methods.items():
                if method['source']=='gift_card':
                    initial_net=amount if mid==old else Decimal(0)
                    method['balance']=float(Decimal(str(method['balance']))+initial_net-observed.get(mid,Decimal(0)))
            check(payments==expected_methods,'Payment method state differs')
            gift={k:Decimal(str(v['balance'])) for k,v in payments.items() if v['source']=='gift_card'}
            gift_ok=gift==expected_gift;zero=all(v==0 for v in observed.values())
            contract=order['status']=='cancelled' and zero and gift_ok
            check(measure['cancellation_contract_met']==contract and measure['per_method_net_zero']==zero and measure['expected_cancelled_gift_balances_met']==gift_ok,'Contract report differs')
            previous=order['payment_history'];counts['native_calls']+=1
        counts[kind]+=1;counts[kind+'_contract_met']+=contract
        counts[kind+'_normal_return']+=1;counts[kind+'_cancelled']+=1
        if new is not None:
            types[methods[old]['source']+'->'+methods[new]['source']]+=1
            counts['composition_gift_balance_mismatch']+=not gift_ok
            if len(examples)<2:examples.append(dict(order_id=oid,old_payment_type=methods[old]['source'],new_payment_type=methods[new]['source'],initial_amount=str(amount),final_signed_net={k:str(v) for k,v in observed.items()}))
    for key,value in report['counts'].items():check(counts[key]==value,'Count mismatch '+key)
    check(dict(types)==report['payment_type_pairs'],'Type counts')
    check(report['initial_database_sha256']==report['restored_database_sha256'] and report['database_restored'],'Reported restore check')
    check(report['model_calls']==0 and not report['external_connection_attempts'],'Unexpected external calls')
    result=dict(status='independently-recomputed',counts=dict(counts),unique_orders=len(selected),
                unique_orders_with_alternatives=sum(bool(r['alternatives']) for r in selected),payment_type_pairs=dict(types),examples=examples,
                archive_bytes=archive.stat().st_size,archive_sha256=sha(archive.read_bytes()),freeze_commit='91b9e0c',execution=execution,
                source_sha256=sha(Path(__file__).read_bytes()),members={n:dict(bytes=len(b),sha256=sha(b)) for n,b in members.items()},
                scope='Exact offline ledger/state audit of native records, not native reexecution. Runtime reported whole-database restoration; its full final database is not in this archive.',
                deployment_note='First UI command failed parsing before execution; corrected string quoting, then one completed native census.')
    with (ROOT/'research/evidence/native_retail_composition_reanalysis_v1.json').open('x',encoding='utf8') as f:json.dump(result,f,indent=2);f.write('\n')
    with (ROOT/'research/evidence/native_retail_composition_summary_v1.json').open('xb') as f:f.write(members['run/summary.json'])
    print(json.dumps({k:v for k,v in result.items() if k not in ('members','examples')}))


if __name__=='__main__':main()
