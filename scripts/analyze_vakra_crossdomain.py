"""Check all registered replication episodes before any answer-score claims."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--registration',type=Path,default=Path('research/evidence/vakra_crossdomain_setup_audit.json'))
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--call-policy',choices=('single','sequential'),default='single')
    a=p.parse_args()
    selection=json.loads(a.registration.read_bytes())
    grid=json.loads((a.root/'grid_manifest.json').read_bytes())
    assert grid['status']=='complete' and grid['registered_episodes']==240
    assert grid['selection']==selection
    domains=[d['domain'] for d in selection['domains']]
    expected={(d,c,m) for d in domains for c in ('original','coverage_check') for m in ('qwen3','qwen25')}
    assert len(grid['workers'])==12
    assert {(w['domain'],w['condition'],w['model']) for w in grid['workers']}==expected
    assert all(w['exit_code']==0 for w in grid['workers'])
    manifests={};records={};rows=[];groups=[];hashes={}
    for d,c,m in sorted(expected):
        directory=a.root/d/c/m/'shard-0'
        mp=directory/'manifest.json';manifest=json.loads(mp.read_bytes())
        assert (manifest['domain'],manifest['instruction_condition'],manifest['max_steps'],manifest['max_new_tokens'],manifest['max_input_tokens'])==(d,c,20,512,32768)
        assert manifest.get('call_policy','single')==a.call_policy
        assert manifest.get('max_tool_calls',20)==20
        registered=next(x for x in selection['domains'] if x['domain']==d)
        assert manifest['preparation_sha256']==registered['preparation_sha256']
        assert manifest['selected_task_ids']==registered['selected_task_ids']
        cases=sorted(directory.glob('case-*.json'));episodes=[json.loads(f.read_bytes()) for f in cases]
        assert len(cases)==20 and [e['uuid'] for e in episodes]==registered['selected_task_ids']
        manifests[(d,c,m)]=manifest;hashes[mp.relative_to(a.root).as_posix()]=sha(mp)
        for f,e in zip(cases,episodes):
            rel=f.relative_to(a.root).as_posix();hashes[rel]=sha(f)
            trace=e.get('trace',[]);usage=e.get('usage',{})
            tool_records=[record for t in trace for record in t.get('calls',[t]) if 'tool_call' in record]
            if trace:
                assert len(trace)==usage['model_calls']<=20
                assert len(tool_records)==usage['tool_calls']<=20
                assert sum('protocol_error' in t for t in trace)==usage['protocol_errors']
                assert e.get('call_policy','single')==a.call_policy
                replies=[t['reply'] for t in trace if 'reply' in t]
                for k in ('input_tokens','output_tokens'):assert sum(r[k] for r in replies)==usage[k]
            records[(d,c,m,e['uuid'])]=e
            rows.append({'domain':d,'condition':c,'model':m,'uuid':e['uuid'],'source':rel,
                         'termination':e['termination'],'final_answer':e.get('final_answer'),
                         'usage':usage,'completed_generations':sum('reply' in t for t in trace),
                         'protocol_error_messages':dict(Counter(t['protocol_error'] for t in trace if 'protocol_error' in t)),
                         'tool_budget_rejections':sum('tool_budget_rejection' in t for t in trace),
                         'final_at_generation_token_ceiling':bool(e.get('final_answer') is not None and trace and trace[-1].get('reply',{}).get('output_tokens')==manifest['max_new_tokens']),
                         'mcp_flagged_errors':sum(bool(t.get('tool_result',{}).get('isError')) for t in tool_records),
                         'validation_error_payloads':sum(any(x.get('text','').startswith('Input validation error:') for x in t.get('tool_result',{}).get('content',[])) for t in tool_records),
                         'errors':[{k:t[k] for k in ('step','error_type','error','protocol_error') if k in t} for t in trace if 'error' in t or 'protocol_error' in t]})
        rs=[r for r in rows if (r['domain'],r['condition'],r['model'])==(d,c,m)]
        groups.append({'domain':d,'condition':c,'model':m,'n':20,
                       'terminations':dict(Counter(r['termination'] for r in rs)),
                       'usage':{k:sum(r['usage'].get(k,0) for r in rs) for k in ('model_calls','tool_calls','input_tokens','output_tokens','generation_seconds','protocol_errors')},
                       'completed_generations':sum(r['completed_generations'] for r in rs),
                       'protocol_error_messages':dict(sum((Counter(r['protocol_error_messages']) for r in rs),Counter())),
                       'tool_budget_rejections':sum(r['tool_budget_rejections'] for r in rs),
                       'final_at_generation_token_ceiling':sum(r['final_at_generation_token_ceiling'] for r in rs),
                       'mcp_flagged_errors':sum(r['mcp_flagged_errors'] for r in rs),
                       'validation_error_payloads':sum(r['validation_error_payloads'] for r in rs)})
    for d in domains:
        initial=manifests[(d,'original','qwen3')]
        for c in ('original','coverage_check'):
            for m in ('qwen3','qwen25'):
                mm=manifests[(d,c,m)]
                for k in ('queries_sha256','preparation_sha256','selected_task_ids','all_task_ids','source_sha256','agent_prompt_source_sha256','packages','seed','decoder','supplied_prefix'):
                    assert mm[k]==initial[k],(d,c,m,k)
        for m in ('qwen3','qwen25'):
            orig,rem=(manifests[(d,c,m)] for c in ('original','coverage_check'))
            assert orig['instruction_suffix']=='' and rem['instruction_suffix']
            assert orig['model_files_sha256']==rem['model_files_sha256']
            assert orig['model_files_sha256']==manifests[(domains[0],'original',m)]['model_files_sha256']
            assert rem['instruction_suffix']==manifests[(domains[0],'coverage_check',m)]['instruction_suffix']
            for uid in initial['selected_task_ids']:
                x,y=(records[(d,c,m,uid)] for c in ('original','coverage_check'))
                if x.get('trace') and y.get('trace'):
                    a0,b0=x['trace'][0]['input'],y['trace'][0]['input']
                    assert b0[0]['content']==a0[0]['content']+rem['instruction_suffix'] and b0[1:]==a0[1:]
                    assert x['initial_peek']==y['initial_peek'] and x['tools']==y['tools']
    assert len(rows)==240
    report={'purpose':'complete execution audit, not official or semantic answer score',
            'registered_episodes':240,'distinct_tasks':60,'domains':domains,'complete':True,
            'call_policy':a.call_policy,
            'batch_wall_seconds':grid['finished']-grid['started'],
            'registration_sha256':sha(a.registration),'input_sha256':hashes,'groups':groups,'rows':rows}
    with a.output.open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
    print(json.dumps({'complete':True,'groups':groups}))


if __name__=='__main__':main()
