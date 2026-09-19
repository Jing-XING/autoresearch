"""Validate all twelve registered budget pairs and record their answer review.

All twelve complete final responses were read by one unblinded assistant.
Exact name-list checks supplement four positive hockey judgements; they are
not an automatic general semantic scorer or an independent human review.
"""
from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def stable(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,allow_nan=True)
def save(p,x):
    with p.open('x',encoding='utf-8') as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n')


def comma_names(text):
    """Parse only the inspected header/blank-line/comma-list response format."""
    header,body=text.split('\n\n',1)
    if not header.strip() or '\n' in body:raise ValueError('Unexpected response format')
    values=[n.strip() for n in body.split(',')]
    if not all(values):raise ValueError('Empty name')
    return values


def calls(episode):
    return [r for t in episode['trace'] for r in t.get('calls',[t]) if 'tool_call' in r]


def main(output=None):
    ev=ROOT/'research/evidence';archive=ROOT/'results/remote/vakra-output-budget-v2-complete.zip'
    deployment=ROOT/'results/deploy/vakra-output-budget-v2.zip'
    assert archive.stat().st_size==259852 and sha(archive)=='9ad8955cdf0c368412e1e57f1f2ae2b74aedbd4d63f1d79f956e4cf6f71f63d7'
    assert sha(deployment)=='7dea81ad419844bdb3f14c6386e5e6491eb64b0dc06af2e1f34afc86b8e851bd'
    raw=archive.with_suffix('');batch=raw/'runs/vakra-output-budget-v2'
    primary=ROOT/'results/remote/vakra-expansion-v2-complete/runs/vakra-expansion-v2'
    with ZipFile(archive) as z:
        assert len(z.namelist())==49 and z.testzip() is None
        for n in z.namelist():assert (raw/n).resolve().is_relative_to(raw.resolve()) and (raw/n).read_bytes()==z.read(n)
    with ZipFile(deployment) as z:
        source_sha=hashlib.sha256(z.read('autolab/vakra_budget_replay.py')).hexdigest()
        sources={Path(n).name:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('autolab/')}
    grid=json.loads((batch/'grid_manifest.json').read_bytes());workers=grid['workers']
    targets=[('cookbook',1),('ice_hockey_draft',0)]
    arms={(d,i,m,c) for d,i in targets for m in ('qwen3','qwen25','qwen30b') for c in ('original','coverage_check')}
    assert grid['status']=='complete' and grid['registered_episodes']==12 and grid['max_new_tokens']==8192
    assert len(workers)==12 and all(w['exit_code']==0 for w in workers)
    assert {(w['domain'],w['task_index'],w['model'],w['condition']) for w in workers}==arms
    cards_path=ev/'vakra_domain_expansion_sql_cards_v1.json';cards=json.loads(cards_path.read_bytes())['cards']
    ann_path=ev/'vakra_expansion_complete_annotations_v1.json'
    old_labels={r['source']:r for r in json.loads(ann_path.read_bytes())['rows']}
    rows=[];files={}
    for domain,index,model,condition in sorted(arms):
        suffix=Path(domain)/condition/model/'shard-0';folder=batch/suffix;before_folder=primary/suffix
        mp=folder/'manifest.json';metadata=json.loads(mp.read_bytes())
        pp=before_folder/'manifest.json';config=json.loads(pp.read_bytes())
        bp=before_folder/f'case-{index:03d}.json';ap=folder/'case-000.json'
        before=json.loads(bp.read_bytes());after=json.loads(ap.read_bytes())
        assert metadata['primary_configuration']==config and metadata['primary_manifest_sha256']==sha(pp)
        assert metadata['primary_target_sha256']==sha(bp) and metadata['script_sha256']==source_sha
        assert metadata['primary_prefix_sha256']=={f'case-{i:03d}.json':sha(before_folder/f'case-{i:03d}.json') for i in range(index)}
        assert metadata['new_max_new_tokens']==8192 and metadata['status']=='complete' and metadata['pairing_error'] is None
        assert all(metadata[k] for k in ('exact_initial_input_verified','exact_initial_peek_verified','database_unchanged'))
        assert (config['max_steps'],config['max_tool_calls'],config['max_new_tokens'],config['max_input_tokens'])==(20,20,512,32768)
        assert config['call_policy']=='sequential' and config['decoder']=='greedy_native_template' and config['seed']==20260919
        assert config['instruction_condition']==condition and config['domain']==domain
        assert all(sources[n]==h for n,h in config['source_sha256'].items())
        assert metadata['placement']['profile']==config['device_profile']
        expected_devices={'0','1'} if model=='qwen30b' else {'0'}
        assert {str(v).removeprefix('cuda:') for v in metadata['placement']['hf_device_map'].values()}==expected_devices
        assert all(n=='NVIDIA A40' for n in metadata['placement']['visible_device_names'])
        assert before['uuid']==after['uuid']==metadata['target_uuid'] and metadata['task_index']==index
        assert before['query']==after['query'] and stable(before['initial_peek'])==stable(after['initial_peek']) and stable(before['tools'])==stable(after['tools'])
        assert before['trace'][0]['input']==after['trace'][0]['input']
        assert before['termination']==after['termination']==metadata['termination']=='agent_finished'
        assert len(before['trace'])==len(after['trace'])
        for a,b in zip(before['trace'][:-1],after['trace'][:-1]):
            assert a['input']==b['input'] and a['reply']['output_token_ids']==b['reply']['output_token_ids'] and a['reply']['text']==b['reply']['text']
        logical=lambda e:[(r['tool_call']['name'],r['tool_call']['arguments'],r['tool_result']['content'],r['tool_result']['isError']) for r in calls(e)]
        assert logical(before)==logical(after)
        assert before['trace'][-1]['input']==after['trace'][-1]['input']
        old_tokens=before['trace'][-1]['reply']['output_token_ids'];new_tokens=after['trace'][-1]['reply']['output_token_ids']
        assert new_tokens[:len(old_tokens)]==old_tokens
        for episode,limit in [(before,512),(after,8192)]:
            usage=episode['usage'];assert len(episode['trace'])==usage['model_calls']<=20 and len(calls(episode))==usage['tool_calls']<=20
            assert usage['protocol_errors']==0
            for key in ('input_tokens','output_tokens'):assert sum(t['reply'][key] for t in episode['trace'])==usage[key]
            assert all(t['reply']['input_tokens']<=32768 and len(t['reply']['output_token_ids'])==t['reply']['output_tokens']<=limit for t in episode['trace'])
        card=next(r for r in cards if r['domain']==domain and r['task_index']==index)
        required=[r[0] for r in card['answer_rows']];assert len(required)==len(set(required))==(791 if domain=='cookbook' else 129)
        primary_rel=bp.relative_to(primary).as_posix();old=old_labels[primary_rel]
        assert old['source_sha256']==sha(bp) and old['answer_label']=='incorrect'
        positive=domain=='ice_hockey_draft' and model in ('qwen3','qwen30b')
        check=None
        if positive:
            names=comma_names(after['final_answer']);assert Counter(names)==Counter(required)
            assert len(old_tokens)==512 and len(new_tokens)>512
            check=dict(parsed_names=names,missing=[],extra=[],count=129,exact_multiset_match=True)
            reason='All129requirednames are explicitly listed; exact comma-list multiset equals the frozenSQLcard.'
        else:
            assert before['final_answer']==after['final_answer'] and old_tokens==new_tokens
            reason='Unchanged complete final text names only three entries rather than all required '+str(len(required))+'. An offered future retrieval, unspecified remainder or correct total does not complete the requested list.'
        row=dict(domain=domain,task_index=index,uuid=after['uuid'],model=model,condition=condition,
            primary_source=primary_rel,primary_sha256=sha(bp),source=ap.relative_to(batch).as_posix(),source_sha256=sha(ap),
            metadata_sha256=sha(mp),initial_input_equal=True,initial_schema_equal=True,initial_peek_equal=True,
            all_pre_final_inputs_and_generated_token_ids_equal=True,tool_actions_and_content_error_results_equal=True,
            final_generation_input_equal=True,primary_final_token_ids_are_prefix=True,
            primary_final_tokens=len(old_tokens),new_final_tokens=len(new_tokens),
            primary_answer_label=old['answer_label'],answer_label='correct' if positive else 'incorrect',reason=reason,
            final_answer=after['final_answer'],primary_final_answer=before['final_answer'],name_check=check,
            before_usage=before['usage'],after_usage=after['usage'],termination=after['termination'])
        rows.append(row)
        for path in (mp,ap,folder/'initialization.json',folder/'server.stderr.log'):files[path.relative_to(batch).as_posix()]=sha(path)
    assert len(list(batch.rglob('case-*.json')))==len(rows)==12
    report=dict(scope=__doc__,complete=True,registered_runs=12,distinct_tasks=2,rows=rows,
        totals=dict(original_correct=0,new_correct=sum(r['answer_label']=='correct' for r in rows),all_final_answers=12,
                    unchanged_final_answers=sum(r['final_answer']==r['primary_final_answer'] for r in rows),
                    all_initial_and_pre_final_pairs_equal=True,protocol_errors=0,input_budget_failures=0,new_final_ceiling_cases=0),
        artifact=dict(path=archive.relative_to(ROOT).as_posix(),sha256=sha(archive),bytes=archive.stat().st_size,entries=49),
        deployment_sha256=sha(deployment),replay_script_sha256=source_sha,raw_sha256=files,
        cards_sha256=sha(cards_path),primary_annotations_sha256=sha(ann_path),script_sha256=sha(Path(__file__)),
        batch_wall_seconds=grid['finished']-grid['started'],
        limits=['One unblinded assistant review of all12completefinaltexts; mechanicalexactnamecheck forfourpositivecases.',
                'Two length-selected tasks and six repeated model/prompt arms, not twelve independent tasks or a general gain estimate.',
                'The intervention changed every generation ceiling. Observed histories happen to match before final generation; this does not establish final-only equivalence in other tasks.',
                'No new controller, acquired-evidence sufficiency or official benchmark scoring claim. Primary420scores remain unchanged.',
                'Warmup/prefix replay assertions are runtime provenance, not separately saved second copies of every replayed response.'])
    save(output or ev/'vakra_output_budget_complete_analysis_v1.json',report)
    print(json.dumps(report['totals']));print(json.dumps([{k:r[k] for k in ('domain','model','condition','primary_final_tokens','new_final_tokens','answer_label')} for r in rows]))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,help='New report path; existing evidence is never overwritten')
    main(parser.parse_args().output)
