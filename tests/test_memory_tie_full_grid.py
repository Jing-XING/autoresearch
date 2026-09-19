"""Synthetic complete-grid integration tests; no real test-set outputs are read."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sys
import zipfile

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from analyze_memory_tie_transfer import analyze, WRAPPER


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value),encoding='utf8')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope='module')
def grid(tmp_path_factory):
    base=tmp_path_factory.mktemp('synthetic-memory-grid');root=base/'runs'
    ids=[f'synthetic-task-{i:02}' for i in range(40)]
    ties=['record_id','alternative_1','alternative_2'];conditions=['full_metadata','boundary_aware'];models=['qwen3','qwen25']
    bank={'source_task_ids':['synthetic-source'], 'records':[
        {'record_id':f'source-{t}','memories':{c:f'{c} lesson {t}' for c in conditions},
         'curation_usage':{c:{'input_tokens':1,'output_tokens':1} for c in conditions}}
        for t in ties]}
    bank_path=base/'bank.json';write(bank_path,bank)
    reg={'batch':'original','registered_episodes':560,'selected_task_ids':ids,'source_bank_sha256':sha(bank_path),
         'tie_orders':ties,'memory_conditions':conditions,'models':models,'rows':[
             {'task_id':t,'ticket_sha256':f'group-{i%2}','choices':{tie:{'record_id':f'source-{tie}'} for tie in ties}}
             for i,t in enumerate(ids)]}
    reg_path=base/'registration.json';write(reg_path,reg)
    code=base/'code.zip';source=b'# synthetic fixture only\n'
    with zipfile.ZipFile(code,'x') as z:z.writestr('autolab/fixture.py',source)
    dep=base/'deployment.json';write(dep,{'batch':'restarted','source_archive_sha256':sha(code)})
    arms=[('record_id','none')]+[(t,c) for t in ties for c in conditions]
    workers=[]
    for tie,condition in arms:
        for model in models:
            for shard in (0,1):
                folder=root/tie/condition/model/f'shard-{shard}'
                workers.append(dict(tie_order=tie,condition=condition,model=model,shard=shard,exit_code=0))
                manifest=dict(batch='original',model=model,task_split='test',all_task_ids=ids,selected_task_ids=ids[shard::2],
                    shard=shard,shards=2,condition=condition,tie_order=tie,registration_sha256=sha(reg_path),memory_bank_sha256=sha(bank_path),
                    seed=20260919,decoder='greedy_native_template_tool_prefix',supplied_prefix='<tool_call>\n',
                    max_new_tokens=512,max_steps=60,max_errors=5,source_sha256={'fixture.py':hashlib.sha256(source).hexdigest()},
                    tau_source_manifest_sha256='synthetic-tau',packages={'fixture':'1'},model_files_sha256={'model':model},
                    task_sha256={t:hashlib.sha256(t.encode()).hexdigest() for t in ids[shard::2]})
                write(folder/'manifest.json',manifest)
                write(folder/'config.json',dict(domain='telecom',max_steps=60,max_errors=5,seed=20260919,enforce_communication_protocol=True))
                statuses=[]
                for index,t in enumerate(ids[shard::2]):
                    i=ids.index(t);reward=int(i%3==0) if condition=='none' else int(10<=i<30) if condition=='boundary_aware' else int(i<20)
                    empty=(condition=='none' and model=='qwen25' and i==0)
                    if empty:reward=None
                    status=dict(task_id=t,reward=reward,model_calls=0 if empty else 1)
                    if empty:status['error_type']='SyntheticPreGenerationError'
                    else:status['termination']='synthetic_stop'
                    calls=[]
                    if not empty:
                        policy='synthetic policy'
                        if condition!='none':policy+=WRAPPER+json.dumps({'prior_experience':f'{condition} lesson {tie}'},ensure_ascii=False)
                        messages=[{'role':'system','content':policy},{'role':'user','content':t}]
                        call=dict(step=0,input=messages,tools=[{'name':'synthetic_noop'}],input_sha256=hashlib.sha256(json.dumps(messages,sort_keys=True).encode()).hexdigest(),
                                  reply={'input_tokens':10,'output_tokens':2,'elapsed_seconds':0.1,'token_ids':[1,2]})
                        if condition!='none':call['memory_selection']=dict(condition=condition,tie_order=tie,record_id=f'source-{tie}')
                        calls=[call]
                        write(folder/f'case-{index:03d}.json',dict(task_id=t,reward_info={'reward':reward},termination_reason='synthetic_stop'))
                    write(folder/f'case-{index:03d}-status.json',status)
                    write(folder/f'case-{index:03d}-model-audit.json',dict(task_id=t,calls=calls))
                    statuses.append(status)
                write(folder/'summary.json',dict(rows=statuses,n=20,successes=sum(r['reward']==1 for r in statuses),errors=sum(r['reward'] is None for r in statuses)))
    write(root/'grid_manifest.json',dict(batch='restarted',status='complete',selection=reg,workers=workers))
    return root,reg_path,bank_path,code,dep


def test_complete_grid_and_error_denominator(grid):
    result=analyze(*grid)
    assert result['registered_episodes']==len(result['rows'])==560
    assert len(result['groups'])==14 and result['first_input_observed_episodes']==559
    assert len(result['no_first_input_episodes'])==1
    none=next(r for r in result['groups'] if r['condition']=='none' and r['model']=='qwen25')
    assert (none['tasks'],none['successes'],none['errors'])==(40,13,1)
    for row in result['contrasts']['record_id_boundary_minus_full']['paired']:
        assert len(row['wins'])==len(row['losses'])==10 and row['success_difference']==0
        assert len(row['joint_successes'])==len(row['joint_nonsuccesses'])==10
    assert result['deployment_batch']=='restarted'


@contextmanager
def edited(path,mutate):
    before=path.read_bytes() if path.exists() else None
    try:
        value=json.loads(before) if before else {}
        mutate(value);write(path,value);yield
    finally:
        if before is None:path.unlink()
        else:path.write_bytes(before)


def test_reject_incomplete_extra_and_conflicting_artifacts(grid):
    root=grid[0];folder=root/'record_id/none/qwen25/shard-0'
    cases=[(root/'grid_manifest.json',lambda x:x.update(status='running'),'incomplete'),
           (grid[-1],lambda x:x.update(batch='wrong'),'batch'),
           (folder/'case-999-status.json',lambda x:x.update(task_id='extra'),'extra case'),
           (folder/'case-000.json',lambda x:x.update(reward_info={'reward':1}),'conflicting simulation'),
           (folder/'case-001.json',lambda x:x['reward_info'].update(reward=1),'simulation/status')]
    for path,mutate,message in cases:
        with edited(path,mutate),pytest.raises(ValueError,match=message):analyze(*grid)
    missing=folder/'case-001-status.json';saved=missing.read_bytes()
    try:
        missing.unlink()
        with pytest.raises(FileNotFoundError):analyze(*grid)
    finally:missing.write_bytes(saved)


def test_reject_changed_policy_and_undocumented_worker(grid):
    root=grid[0];path=root/'record_id/full_metadata/qwen3/shard-0/case-000-model-audit.json'
    def change(x):
        call=x['calls'][0];call['input'][1]['content']='different target'
        call['input_sha256']=hashlib.sha256(json.dumps(call['input'],sort_keys=True).encode()).hexdigest()
    with edited(path,change),pytest.raises(ValueError,match='Initial policy'):analyze(*grid)
    extra=root/'record_id/none/qwen3/shard-2/manifest.json'
    with edited(extra,lambda x:x.update(extra=True)),pytest.raises(ValueError,match='worker manifest'):analyze(*grid)
