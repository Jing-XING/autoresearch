"""Recompute selected recovery-paper tables from a portable offline ZIP.

Python 3.10+ standard library only. Does not execute third-party code, import
model libraries, extract files, contact a service or rerun native experiments.
"""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from decimal import Decimal
import hashlib
from io import BytesIO
import json
from pathlib import Path, PurePosixPath
from zipfile import ZipFile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check(ok, message):
    if not ok:
        raise ValueError(message)


def safe_name(name):
    p = PurePosixPath(name)
    return bool(name) and not p.is_absolute() and '..' not in p.parts and '\\' not in name and ':' not in name


class Artifact:
    def __init__(self, path):
        self.zip = ZipFile(path)
        names = self.zip.namelist()
        check(len(names) == len(set(names)), 'Duplicate ZIP names')
        check(all(safe_name(n) for n in names), 'Unsafe ZIP name')
        check(self.zip.testzip() is None, 'ZIP CRC mismatch')
        self.manifest = json.loads(self.zip.read('artifact_manifest.json'))
        check(self.manifest['format'] == 'paper3-offline-v1', 'Unknown artifact format')
        check(set(names) == set(self.manifest['files']) | {'artifact_manifest.json'}, 'Incomplete or extra artifact members')
        for name, metadata in self.manifest['files'].items():
            data = self.zip.read(name)
            check(len(data) == metadata['bytes'] and sha(data) == metadata['sha256'], 'Member mismatch: '+name)
        self.aliases = self.manifest['original_path_aliases']
        check(all(v in self.manifest['files'] for v in self.aliases.values()), 'Unresolved original path')

    def read(self, name, digest=None):
        name = self.aliases.get(name, name)
        check(name in self.manifest['files'], 'Unregistered member: '+name)
        data = self.zip.read(name)
        check(digest is None or sha(data) == digest, 'Raw source digest mismatch: '+name)
        return data

    def obj(self, name, digest=None):
        return json.loads(self.read(name, digest))

    def evidence(self, stem):
        return self.obj('research/evidence/'+stem+'.json')


def native_airline(a):
    report = a.evidence('tau_airline_compensation_probe_v1')
    fixture = a.obj('research/evidence/tau_airline_compensation_preflight_v1.json', report['preflight_sha256'])
    fixtures = {r['metadata']['profile']:r for r in fixture['cases']}
    profiles=('single_card','two_leg_mixed')
    faults=('normal','native_error_before_effect','shadow_only','error_after_effect')
    clients=('rac_default','rac_raise_control','agent_saga')
    expected={(p,f,c) for p in profiles for f in faults for c in clients}
    expected.add(('single_card','normal','rac_unadapted_mapper'))
    rows=report['cases']; seen=set(); states={}; groups=defaultdict(list); wal_count=0
    table=[]
    for row in rows:
        key=tuple(row[k] for k in ('profile','fault','condition'))
        check(key not in seen and key in expected,'Unexpected/duplicate native cell');seen.add(key)
        state=a.obj(row['raw_state_file'],row['raw_state_sha256'])
        initial=fixtures[row['profile']]['before']
        check(state['before']==initial,'Native fixture initial state differs')
        check(state['booking']==fixtures[row['profile']]['booking'],'Native booking differs')
        rid=row['reservation_id']; now=state['current']; reservation=now['reservations'][rid]
        check(set(now['reservations'])-set(initial['reservations'])=={rid},'Reservation set differs')
        check(all(now['reservations'][k]==v for k,v in initial['reservations'].items()),'Existing reservation changed')
        contract=reservation.get('status')=='cancelled' and sum(Decimal(str(p['amount'])) for p in reservation['payment_history'])==0
        check(contract==row['oracle']['cancellation_contract_met'],'Reported native contract differs')
        check(now!=initial and row['oracle']['full_database_restored'] is False,'Unexpected full restoration')
        for flight in state['booking']['flights']:
            fn,date,cabin=flight['flight_number'],flight['date'],state['booking']['cabin']
            check(now['flights'][fn]['dates'][date]['available_seats'][cabin]==initial['flights'][fn]['dates'][date]['available_seats'][cabin]-1,'Seat state differs')
        if 'wal_file' in row:
            events=[json.loads(line) for line in a.read(row['wal_file'],row['wal_sha256']).splitlines() if line.strip()]
            check(bool(events),'Empty WAL');wal_count+=1
        if row['condition']!='rac_unadapted_mapper':
            check(len(state['calls'])==2,'Unexpected native call count')
            groups[key[:2]].append(now)
        else:
            check(len(state['calls'])==1 and not contract,'Unadapted control no longer matches')
        states[key]=state
        table.append(dict(profile=key[0],fault=key[1],client=key[2],contract=contract,
                          states=row['states_after'],report=row['rollback_report'],exception=row.get('rollback_exception')))
    check(seen==expected and len(rows)==25,'Missing native matrix cells')
    check(all(len(v)==3 and v[0]==v[1]==v[2] for v in groups.values()),'Cross-client state inequality')
    for p in profiles:
        for c in clients:
            x,y=states[p,'normal',c],states[p,'shadow_only',c]
            check(x['calls'][1]['native_result']==y['calls'][1]['native_result'] and x['current']!=y['current'],'Same-response counterexample differs')
    return dict(executions=25,wal_files=wal_count,equal_state_groups=len(groups),same_response_different_state_pairs=6,rows=table)


def retry_census(a):
    report=a.evidence('tau_airline_retry_census_v1')
    source=a.obj('results/third_party/tau2-bench/data/tau2/domains/airline/db.json',report['database_sha256'])['reservations']
    data=a.read(report['raw'],report['raw_sha256']);check(len(data)==report['raw_bytes'],'Census byte count differs')
    seen=set();counts=Counter();payments=Counter();patterns=Counter()
    for line in data.splitlines():
        row=json.loads(line);rid=row['reservation_id']
        check(rid in source and rid not in seen,'Unexpected/duplicate reservation');seen.add(rid)
        initial=deepcopy(source[rid]);check('status' not in initial,'Unexpected initial status');initial['status']=None
        check(initial==row['before'] and len(initial['payment_history'])==1,'Initial census value differs')
        payments[initial['payment_history'][0]['payment_id'].rsplit('_',1)[0]]+=1
        check(set(row['policies'])=={'single','blind_three','read_before_retry'},'Census policy set differs')
        for policy,n in [('single',1),('blind_three',3),('read_before_retry',1)]:
            result=row['policies'][policy];check(len(result['steps'])==n,'Missing census step')
            current=deepcopy(initial)
            for step in result['steps']:
                current['payment_history'] += [{'payment_id':p['payment_id'],'amount':-p['amount']} for p in current['payment_history']]
                current['status']='cancelled'
                check(current==step['state']==step['native_payload'],'Cancellation transition mismatch')
                amounts=[Decimal(str(p['amount'])) for p in current['payment_history']]
                measurement=step['measurement']
                check(sum(amounts,Decimal(0))==Decimal(measurement['net'])==0 and measurement['contract_met'] is True,'Net/contract mismatch')
                check(measurement['entries']==len(amounts),'Ledger length mismatch')
                check(Decimal(measurement['positive'])==sum((v for v in amounts if v>0),Decimal(0)),'Positive ledger mismatch')
                check(Decimal(measurement['negative'])==sum((v for v in amounts if v<0),Decimal(0)),'Negative ledger mismatch')
                ack=step['imposed_ack_error']
                check(ack is None if policy=='single' else ack=={'type':'RuntimeError','message':'Constructed acknowledgement error after native cancellation'},'Acknowledgement condition mismatch')
                counts['cancels']+=1;counts['ack_errors']+=policy!='single'
            check(result['final']==current,'Final census state mismatch')
            check(result['final_sha256']==sha(json.dumps(current,sort_keys=True,separators=(',',':')).encode()),'Final state digest mismatch')
            if policy=='read_before_retry':
                check(result['read_payload']==current and result['stopped_on_contract'] is True,'Native read mismatch');counts['reads']+=1
            else:
                check(result['read_payload'] is None and result['stopped_on_contract'] is None,'Unexpected read')
        p=row['policies']
        check(p['single']['final']==p['read_before_retry']['final']!=p['blind_three']['final'],'Policy equality mismatch')
        patterns[tuple(len(s['state']['payment_history']) for s in p['blind_three']['steps'])]+=1
    check(seen==set(source) and len(seen)==2000,'Census not complete')
    check(counts=={'cancels':10000,'ack_errors':8000,'reads':2000},'Census count mismatch')
    check(report['initial_model_database_sha256']==report['restored_model_database_sha256'],'Reported restoration mismatch')
    return dict(population=len(seen),**counts,ledger_patterns={str(k):v for k,v in patterns.items()},initial_payment_types=dict(payments),read_policy_equal_to_single=2000,blind_policy_equal_to_single=0)


def archive_audit(a):
    expected=a.evidence('rac_zenodo_archive_audit_v1')
    data=a.read('results/third_party/rac/zenodo-19753969.zip',expected['archive_sha256'])
    records=[];unique=set();groups=defaultdict(list);mismatch=[];counts=Counter();compensations=Counter();jsons=[]
    with ZipFile(BytesIO(data)) as z:
        check(z.testzip() is None and len(z.namelist())==470,'Upstream ZIP mismatch')
        for name in z.namelist():
            if not name.endswith('.json'):continue
            raw=z.read(name);obj=json.loads(raw);short=name.split('/',1)[1]
            jsons.append(dict(path=short,sha256=sha(raw),bytes=len(raw),keys=sorted(obj)))
            if '/all_tasks/' in name:
                counts['aggregate_files']+=1
                for record in obj['results']:
                    records.append(record);unique.add(sha(json.dumps(record,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()))
            elif '/Tau^2 Bench/' in name:counts['tau_files']+=1
            elif '/REALMBench/' in name:
                counts['realm_files']+=1
                compensations[obj['framework']]+=sum(e.get('success') is True for e in obj['compensation_events'])
                if obj['start_time'] is not None:groups[obj['framework'],obj['task_id'],str(obj['start_time'])].append(obj['events'])
                for event in obj['events']:
                    result=event.get('result')
                    if isinstance(result,str):
                        try:result=json.loads(result)
                        except ValueError:pass
                    error=isinstance(result,dict) and (result.get('success') is False or result.get('isError') is True or str(result.get('status','')).lower() in ('error','failed','failure'))
                    if error and event.get('success') is True:mismatch.append((name,event))
            else:raise ValueError('Unclassified archive JSON')
    check(jsons==expected['json_members'],'Archive member inventory differs')
    check(len(records)==expected['aggregate_record_occurrences']==1272 and len(unique)==expected['aggregate_exact_distinct_records']==224,'Aggregate count mismatch')
    chains=[]
    for items in groups.values():
        if len(items)<2:continue
        items=sorted(items,key=len);check(all(l==r[:len(l)] for l,r in zip(items,items[1:])),'Snapshot not prefix chain');chains.append(len(items))
    check(chains==[35] and not mismatch and expected['realm_structured_status_mismatches']==[],'Archive contradiction/prefix result differs')
    check(compensations['react_agent_compensation']==9,'RAC compensation occurrence count differs')
    return dict(json_files=len(jsons),**counts,aggregate_occurrences=len(records),distinct_aggregate_records=len(unique),prefix_chain_sizes=chains,structured_status_mismatches=len(mismatch),
                successful_compensation_record_occurrences_by_framework=dict(compensations),
                compensation_count_scope='Raw record occurrences across files, including repeated snapshots; not distinct actions, independent trials or verified effect outcomes.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',type=Path);parser.add_argument('--sha256',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    check(sha(args.archive.read_bytes())==args.sha256,'Outer archive digest differs from supplied receipt')
    a=Artifact(args.archive)
    try:
        result=dict(scope='Offline byte integrity and arithmetic/state reanalysis; no experiment reexecution or submission-readiness certification.',
                    archive_sha256=args.sha256,member_count=len(a.manifest['files']),
                    native_airline=native_airline(a),retry_census=retry_census(a),published_archive=archive_audit(a),
                    unchecked_scope='Other probe reports are byte-verified and available for inspection. Their recorded boolean assertions, dependency provenance and execution behavior are not independently reexecuted by this command.')
    finally:a.zip.close()
    with args.output.open('x',encoding='utf8') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:result[k] for k in ('archive_sha256','member_count','retry_census','published_archive')}))


if __name__=='__main__':main()
