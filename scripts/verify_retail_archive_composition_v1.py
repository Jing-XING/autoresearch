"""Independently re-count the fixed archive screen using rational arithmetic."""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path


def sha(raw): return hashlib.sha256(raw).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path('.'))
    p.add_argument('--audit',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();root=args.root
    reg_path=root/'research/evidence/retail_archive_composition_registration_v1.json'
    reg=json.loads(reg_path.read_bytes());audit=json.loads(args.audit.read_bytes())
    assert audit['registration_sha256']==sha(reg_path.read_bytes())
    for rel,h in reg['analysis_inputs'].items():assert sha((root/rel).read_bytes())==h
    provenance=json.loads((root/'research/evidence/retail_archive_git_provenance_v1.json').read_bytes())
    tree_bytes=(root/'results/audits/retail-archive-github-tree-v1.json').read_bytes()
    assert sha(tree_bytes)==provenance['response_sha256']
    tree=json.loads(tree_bytes);assert not tree['truncated'] and tree['sha']==reg['snapshot_revision']
    entries={e['path']:e for e in tree['tree']}
    by_source={f['file']:f for f in audit['files']}; verified=[];record_count=0;payload_count=0
    assert set(by_source)==set(reg['archives'])
    assert len({(r['source'],r['simulation_index']) for r in audit['records']})==len(audit['records'])
    all_hashes=Counter()
    for name,pin in sorted(reg['archives'].items()):
        rel='data/tau2/results/final/'+name;raw=(root/'results/third_party/tau2-bench'/rel).read_bytes()
        assert sha(raw)==pin['sha256'] and len(raw)==pin['bytes']
        normalized=raw.replace(b'\r\n',b'\n')
        assert hashlib.sha1(('blob '+str(len(normalized))+'\0').encode()+normalized).hexdigest()==entries[rel]['sha']
        data=json.loads(raw);records=[r for r in audit['records'] if r['source']==name]
        assert len(records)==len(data['simulations'])==456
        assert [(r['simulation_index'],r['simulation_id']) for r in records]==[(i,s['id']) for i,s in enumerate(data['simulations'])]
        counts=Counter(simulations=456);scored_tasks=set()
        for rec,sim in zip(records,data['simulations']):
            assert (rec['task_id'],rec['trial'],rec['seed'],rec['original_reward'])==(sim['task_id'],sim['trial'],sim['seed'],sim['reward_info']['reward'])
            all_hashes[sha(json.dumps(sim,sort_keys=True,separators=(',',':')).encode())]+=1
            messages=sim['messages']
            calls=[(mi,ci,c) for mi,m in enumerate(messages) if m['role']=='assistant'
                   for ci,c in enumerate(m.get('tool_calls') or []) if c.get('requestor','assistant')=='assistant']
            selected=[(mi,ci,c) for mi,ci,c in calls if c['name'] in ('modify_pending_order_payment','cancel_pending_order')]
            assert [(r['message_index'],r['call_index'],r['call']) for r in rec['selected_calls']]==selected
            for ri,(mi,ci,call) in enumerate(selected):
                row=rec['selected_calls'][ri];counts[call['name']]+=1
                matches=[(j,m) for j,m in enumerate(messages) if m['role']=='tool' and m['id']==call['id'] and m.get('requestor','assistant')=='assistant']
                assert sum(c['id']==call['id'] for _,_,c in calls)==1 and len(matches)==1 and matches[0][0]>mi
                assert row['association']=='unique_following_result'
                assert row['result_matches']==[dict(message_index=j,message=m) for j,m in matches]
                counts['association_unique_following_result']+=1
                if call['name']!='cancel_pending_order':continue
                earlier=[j for j,(i,_,c) in enumerate(selected[:ri]) if c['name']=='modify_pending_order_payment' and c['arguments'].get('order_id')==call['arguments'].get('order_id')]
                same=[c for i,_,c in calls if i==mi and c['name']=='modify_pending_order_payment' and c['arguments'].get('order_id')==call['arguments'].get('order_id')]
                assert row['earlier_change_indices']==earlier==[]
                assert row['unordered_same_message_changes']==same==[] and row['qualifying_change_indices']==[]
                response=matches[0][1]
                try:order=json.loads(response['content'])
                except (ValueError,TypeError):
                    assert response['error'] is True and row['order'] is None and not row['ledger']['scorable'];continue
                assert order==row['order'] and order['order_id']==call['arguments']['order_id'] and order['status']=='cancelled'
                assert response['error'] is False and row['normal_order_return'] is True
                history=order['payment_history'];assert history
                totals={}
                for item in history:
                    amount=Fraction(str(item['amount']));assert amount>=0 and item['transaction_type'] in ('payment','refund')
                    key=item['payment_method_id'];totals[key]=totals.get(key,Fraction(0))+(amount if item['transaction_type']=='payment' else -amount)
                check=row['ledger'];assert check['scorable'] and check['entries']==len(history)
                assert {k:Fraction(v) for k,v in check['net_by_method'].items()}==totals
                assert check['all_methods_zero']==all(v==0 for v in totals.values())
                counts['scored_cancel_payload']+=1;scored_tasks.add(sim['task_id']);payload_count+=1
                counts['nonzero_cancel_payload']+=not all(v==0 for v in totals.values())
            record_count+=1
        expected=by_source[name]['summary']
        assert all(counts[k]==v for k,v in expected['counts'].items()) and all(expected['counts'].get(k,0)==v for k,v in counts.items())
        assert expected['distinct_tasks']=={'scored_cancel_payload':len(scored_tasks)}
        verified.append(dict(file=name,simulations=456,payment_changes=counts['modify_pending_order_payment'],cancellations=counts['cancel_pending_order'],scored_payloads=counts['scored_cancel_payload'],nonzero_payloads=counts['nonzero_cancel_payload']))
    assert record_count==1824 and payload_count==433 and not any(v>1 for v in all_hashes.values()) and audit['canonical_duplicate_groups']==[]
    result=dict(scope='Independent raw JSON re-count and Fraction ledger arithmetic; no persisted-state or historical runtime verification.',
                audit_sha256=sha(args.audit.read_bytes()),audit_bytes=args.audit.stat().st_size,
                registration_sha256=sha(reg_path.read_bytes()),simulation_records_verified=record_count,
                cancellation_payloads_recomputed=payload_count,qualifying_compositions=0,
                nonzero_payloads=0,git_blob_provenance_verified=True,canonical_duplicates=0,files=verified)
    with args.output.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result))


if __name__=='__main__':main()
