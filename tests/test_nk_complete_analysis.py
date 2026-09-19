"""Synthetic 140-curation/160-target fixtures; no experimental outcomes read."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from autolab.nk_prefix_bank import build_bank
from autolab.nk_prefix_comparator import CONDITIONS, LIMIT, TEXT_LIMITS, VOCABULARIES, prepare
from autolab.nk_prefix_curation import load_prepared
from scripts.analyze_memory_tie_transfer import WRAPPER
from scripts.analyze_nk_test40_v1 import analyze_curation, analyze_targets, sha


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


@contextmanager
def edited(path, mutate):
    before = path.read_bytes() if path.exists() else None
    try:
        value = json.loads(before) if before else {}
        mutate(value)
        write(path, value)
        yield
    finally:
        if before is None:
            path.unlink()
        else:
            path.write_bytes(before)


@pytest.fixture(scope='module')
def fixture(tmp_path_factory):
    base = tmp_path_factory.mktemp('nk-synthetic')
    sources = [f'source-{i:02d}' for i in range(70)]
    for uid in sources:
        write(base / 'inputs' / (uid + '.json'), dict(system_messages=[{'role':'system', 'content':'synthetic'}],
            observed_messages=[], generation_budget=8, observed_generations=8,
            stop_reason='external_generation_cutoff', observed_benchmark_reward=0))
    prepared = base / 'prepared'
    prepare(base / 'inputs', prepared)
    preparation, packets = load_prepared(prepared)
    weights = {'synthetic-model':'synthetic-hash'}
    source_path = base / 'source.json'
    write(source_path, dict(source_task_ids=['training-only'], curation_manifests=[{'configuration':{'model_files_sha256':weights}}],
          records=[dict(record_id=uid, ticket='shared synthetic ticket', source_model='synthetic', memories={'raw':'synthetic raw'}) for uid in sources]))
    source_code = {k:'synthetic-code' for k in ('nk_prefix_curation.py','nk_prefix_comparator.py','local_smoke.py','tool_agent.py')}
    curation_reg = base / 'curation-registration.json'
    write(curation_reg, dict(batch='nk-prefix-curation-v1', preparation_manifest_sha256=sha(prepared/'manifest.json'),
          model_files_sha256=weights, source_files_sha256={'autolab/'+k:v for k,v in source_code.items()}))
    curation_root = base / 'curation'
    totals = {'valid':0, 'invalid':0, 'generation_errors':0}
    for shard in range(4):
        folder = curation_root / f'shard-{shard}'
        write(folder/'manifest.json', dict(schema='autolab.nk_prefix_curation.v1', shard=shard, shards=4,
            preparation=preparation, preparation_manifest_sha256=sha(prepared/'manifest.json'), model_files_sha256=weights,
            source_sha256=source_code, packages={'synthetic':'1'}, decoding='greedy', seed=20260919, max_new_tokens=LIMIT,
            selected_record_ids=sources[shard::4]))
        rows = []
        for uid in sources[shard::4]:
            for condition in CONDITIONS:
                parsed = {'task_id':uid, 'failure':{k:v[0] for k,v in VOCABULARIES.items()}, **{k:'synthetic' for k in TEXT_LIMITS}}
                value = {**packets[uid,condition], 'status':'valid_memory', 'parsed':parsed, 'validation_errors':[],
                         'reply':{'text':json.dumps(parsed), 'input_tokens':10, 'output_tokens':200, 'elapsed_seconds':0.1}}
                if uid == sources[0] and condition == CONDITIONS[0]:
                    from autolab.nk_prefix_comparator import validate_reply
                    parsed_bad, errors = validate_reply('truncated', uid, 1024)
                    value.update(status='invalid_memory', parsed=parsed_bad, validation_errors=errors,
                                 reply={'text':'truncated','input_tokens':10,'output_tokens':1024,'elapsed_seconds':0.1})
                if uid == sources[-1] and condition == CONDITIONS[1]:
                    value = {**packets[uid,condition], 'status':'generation_error', 'error_type':'SyntheticError', 'error':'fixture'}
                write(folder/f'{uid}-{condition}.json',value)
                rows.append({'record_id':uid,'condition':condition,'status':value['status']})
        counts = {k:sum(r['status']==v for r in rows) for k,v in [('valid','valid_memory'),('invalid','invalid_memory'),('generation_errors','generation_error')]}
        write(folder/'summary.json',dict(rows=rows,expected_records=len(rows),**counts))
        for k,v in counts.items(): totals[k]+=v
    write(curation_root/'grid_manifest.json', dict(batch='nk-prefix-curation-v2',status='complete',expected_sources=70,expected_curations=140,
          workers=[{'gpu':i,'exit_code':0} for i in range(4)],outcomes=totals))
    with patch('autolab.nk_prefix_bank.SOURCE_BANK_SHA',sha(source_path)):
        bank = build_bank(prepared,curation_root,source_path,curation_reg)
    bank_path = base/'bank.json'; write(bank_path,bank)
    ids = [f'test-{i:02}' for i in range(40)]
    tickets = [g for g,n in enumerate((13,3,8,1,15)) for _ in range(n)]
    selection = dict(preparation_manifest_sha256=sha(prepared/'manifest.json'),selected_source_ids=sources,rows=[
        dict(task_id=uid,ticket_sha256=f'ticket-{tickets[i]}',source_choice={'record_id':sources[tickets[i]],'similarity':1,'tied_candidates':70,'pool_size':70})
        for i,uid in enumerate(ids)])
    selection_path=base/'selection.json';write(selection_path,selection)
    reg=dict(batch='tau-nk-test40-v1',registered_episodes=160,target_count=40,conditions=list(CONDITIONS),models=['qwen3','qwen25'],
             selection_sha256=sha(selection_path),curation_registration_sha256=sha(curation_reg),source_files_sha256={'synthetic':'source'},
             model_files_sha256={m:{'model':m} for m in ('qwen3','qwen25')})
    reg_path=base/'target-registration.json';write(reg_path,reg)
    root=base/'targets';workers=[]
    for condition in CONDITIONS:
        for model in reg['models']:
            for shard in range(2):
                folder=root/condition/model/f'shard-{shard}'
                workers.append(dict(condition=condition,model=model,shard=shard,exit_code=0))
                write(folder/'manifest.json',dict(batch=reg['batch'],model=model,task_split='test',all_task_ids=ids,selected_task_ids=ids[shard::2],
                    shard=shard,shards=2,condition=condition,registration_sha256=sha(reg_path),selection_sha256=sha(selection_path),memory_bank_sha256=sha(bank_path),
                    seed=20260919,decoder='greedy_native_template_tool_prefix',supplied_prefix='<tool_call>\n',max_new_tokens=512,max_steps=60,max_errors=5,
                    source_sha256=reg['source_files_sha256'],model_files_sha256=reg['model_files_sha256'][model],tau_source_manifest_sha256='synthetic-tau',
                    packages={'synthetic':'1'},task_sha256={uid:hashlib.sha256(uid.encode()).hexdigest() for uid in ids[shard::2]}))
                write(folder/'config.json',dict(domain='telecom',max_steps=60,max_errors=5,seed=20260919,enforce_communication_protocol=True))
                statuses=[]
                for index,uid in enumerate(ids[shard::2]):
                    i=ids.index(uid);chosen=selection['rows'][i]['source_choice'];source=bank['records'][tickets[i]]
                    memory=source['memories'][condition];state=source['curation'][condition]['status']
                    pre_error=(model=='qwen25' and condition==CONDITIONS[1] and i==39)
                    reward=None if pre_error else int(i<20) if condition==CONDITIONS[0] else int(10<=i<30)
                    status=dict(task_id=uid,reward=reward,model_calls=0 if pre_error else 1)
                    if pre_error:status['error_type']='SyntheticPreGenerationError'
                    else:status['termination']='synthetic_end'
                    calls=[]
                    if not pre_error:
                        inputs=[{'role':'system','content':'policy'+WRAPPER+json.dumps({'prior_experience':memory},ensure_ascii=False)}, {'role':'user','content':uid}]
                        calls=[dict(step=0,input=inputs,tools=[{'name':'synthetic'}],input_sha256=hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest(),
                            reply={'input_tokens':11,'output_tokens':3,'elapsed_seconds':0.1},
                            memory_selection={**chosen,'condition':condition,'curation_status':state,'memory_sha256':hashlib.sha256(memory.encode()).hexdigest()})]
                        write(folder/f'case-{index:03d}.json',dict(task_id=uid,reward_info={'reward':reward},termination_reason='synthetic_end'))
                    write(folder/f'case-{index:03d}-status.json',status)
                    write(folder/f'case-{index:03d}-model-audit.json',dict(task_id=uid,calls=calls));statuses.append(status)
                write(folder/'summary.json',dict(rows=statuses,n=20,successes=sum(s['reward']==1 for s in statuses),errors=sum(s['reward'] is None for s in statuses)))
    write(root/'grid_manifest.json',dict(status='complete',batch='tau-nk-test40-v2',registered_episodes=160,registration=reg,workers=workers))
    return (root,reg_path,selection_path,bank_path),(curation_root,prepared,source_path,curation_reg,bank_path)


def test_complete_grid_preserves_failure_and_empty_memory(fixture):
    target, curation = fixture
    result=analyze_targets(*target)
    assert result['registered_episodes']==len(result['rows'])==160
    assert result['first_input_observed_episodes']==159
    assert len(result['no_first_input_episodes'])==1
    for p in result['primary_boundary_minus_schema']:
        assert [len(p[k]) for k in ('wins','losses','joint_successes','joint_nonsuccesses')]==[10,10,10,10]
    for group in result['groups']:
        assert group['tasks']==40 and group['successes']==20
        assert group['empty_memory_episodes']==(13 if group['condition']==CONDITIONS[0] else 0)
        assert group['distinct_memory_texts_including_empty']==5
    assert sorted(g['tasks'] for g in result['descriptive_group_sensitivity'][0]['visible_ticket_groups'])==[1,3,8,13,15]
    for sensitivity in result['descriptive_group_sensitivity']:
        assert sensitivity['task_equal_difference']==0
        assert sensitivity['group_equal_difference']==pytest.approx((-10/13+0+4/8+1+5/15)/5)
        first=sensitivity['visible_ticket_groups'][0]
        assert first['leave_group_out_difference']==pytest.approx(10/27)
    with patch('autolab.nk_prefix_bank.SOURCE_BANK_SHA',sha(curation[2])):
        report=analyze_curation(*curation)
    assert report['bank_reconstructed'] and report['curations']==140
    assert report['groups'][0]['status_counts']=={'invalid_memory':1,'valid_memory':69}
    assert report['groups'][1]['generation_errors_without_usage']==1


def test_target_mutations_rejected(fixture):
    target,_=fixture;root=target[0];folder=root/CONDITIONS[1]/'qwen25/shard-1'
    def input_change(x):
        c=x['calls'][0];c['input'][1]['content']='changed'
        c['input_sha256']=hashlib.sha256(json.dumps(c['input'],sort_keys=True).encode()).hexdigest()
    for path,mutate,message in [
        (root/'grid_manifest.json',lambda x:x.update(status='running'),'incomplete'),
        (folder/'case-019.json',lambda x:x.update(invalid=True),'case artifact'),
        (folder/'case-999-status.json',lambda x:x.update(invalid=True),'case artifact'),
        (folder/'case-000.json',lambda x:x['reward_info'].update(reward=1),'Official result'),
        (folder/'case-000-model-audit.json',input_change,'Initial policy'),
        (folder/'case-000-model-audit.json',lambda x:x['calls'][0]['memory_selection'].update(curation_status='invalid_memory'),'curation quality'),
        (folder/'manifest.json',lambda x:x.update(packages={'changed':'version'}),'runtime changed'),
        (folder/'case-000-model-audit.json',lambda x:x['calls'][0]['reply'].update(input_tokens=-1),'generation usage')]:
        with edited(path,mutate),pytest.raises(ValueError,match=message):analyze_targets(*target)


def test_curation_reconstruction_rejects_extra_or_altered_reply(fixture):
    _,args=fixture;root=args[0]
    with patch('autolab.nk_prefix_bank.SOURCE_BANK_SHA',sha(args[2])):
        with edited(root/'shard-0/extra.json',lambda x:x.update(extra=True)),pytest.raises(ValueError,match='Unexpected curation'):analyze_curation(*args)
        path=root/'shard-0/source-00-nk_schema_boundary.json'
        with edited(path,lambda x:x['reply'].update(text='different')),pytest.raises(ValueError,match='validation disagrees'):analyze_curation(*args)
