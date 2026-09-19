"""Descriptive conditional uncertainty and retained annotation sensitivity.

Exact finite bootstrap distribution over task pairs within each fixed domain;
not a population interval over domains, a new method, or a preregistered test.
"""
from collections import Counter,defaultdict
import argparse
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from autolab.vakra_review_summary import summarize_review


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def exact_bootstrap(strata):
    """Distribution of the sum under within-stratum paired resampling."""
    pmf={0:Fraction(1)};n=sum(len(s) for s in strata)
    assert n and all(s and set(s)<={-1,0,1} for s in strata)
    for values in strata:
        counts=Counter(values)
        one={v:Fraction(c,len(values)) for v,c in counts.items()}
        for _ in values:
            nxt=defaultdict(Fraction)
            for total,p in pmf.items():
                for value,q in one.items():nxt[total+value]+=p*q
            pmf=dict(nxt)
    assert sum(pmf.values())==1
    assert sum(k*v for k,v in pmf.items())==sum(sum(s) for s in strata)
    def quantile(q):
        cumulative=Fraction(0)
        for total,p in sorted(pmf.items()):
            cumulative+=p
            if cumulative>=q:return total
        raise AssertionError('Invalid PMF')
    lo,hi=quantile(Fraction(1,40)),quantile(Fraction(39,40))
    return dict(n=n,observed_net_gain=sum(sum(s) for s in strata),
        interval_net_gain=[lo,hi],interval_percentage_points=[100*lo/n,100*hi/n],
        pmf=[{'net_gain':k,'probability':str(v)} for k,v in sorted(pmf.items())])


def analyze(annotations,summary,rules):
    joined=summarize_review(summary,annotations,rules)
    rows={(r['domain'],r['uuid'],r['model'],r['condition']):r for r in annotations['rows']}
    result=[]
    for model in summary['models']:
        strata=[];domain_rows=[]
        for domain in summary['domains']:
            tasks=[r for r in rules if r['domain']==domain and r['interpretation_stratum']!='ambiguous']
            deltas=[]
            for task in tasks:
                a,b=[rows[domain,task['uuid'],model,c]['answer_label']=='correct' for c in ('original','coverage_check')]
                deltas.append(int(b)-int(a))
            strata.append(deltas);domain_rows.append(dict(domain=domain,n=len(deltas),net_gain=sum(deltas)))
        totals=[r for r in joined['groups'] if r['domain']=='all' and r['model']==model]
        pair=next(r for r in joined['paired'] if r['domain']=='all' and r['model']==model)
        result.append(dict(model=model,original_correct=totals[0]['correct'],reminder_correct=totals[1]['correct'],
            gains=len(pair['gains']),losses=len(pair['losses']),difference_percentage_points=pair['difference_percentage_points'],
            domain_deltas=domain_rows,conditional_paired_bootstrap=exact_bootstrap(strata),
            leave_one_domain_out=[dict(omitted=r['domain'],n=49-r['n'],difference_percentage_points=100*(sum(sum(s) for s in strata)-r['net_gain'])/(49-r['n'])) for r in domain_rows]))
    return result


def main(output=None):
    ev=ROOT/'research/evidence';ep=ev/'vakra_expansion_complete_grid_v1.json';ap=ev/'vakra_expansion_complete_annotations_v1.json'
    cp=ev/'vakra_domain_expansion_sql_cards_v1.json';dp=ev/'vakra_expansion_disney_review_sensitivity_v1.json'
    summary=json.loads(ep.read_bytes());ann=json.loads(ap.read_bytes());rules=json.loads(cp.read_bytes())['cards']
    sensitivity=json.loads(dp.read_bytes());strict=deepcopy(ann)
    changes={r['source']:r for r in sensitivity['changed_answers']};assert len(changes)==8
    changed=0
    for r in strict['rows']:
        if r['source'] in changes:
            assert r['source_sha256']==changes[r['source']]['source_sha256'] and r['answer_label']=='correct'
            r['answer_label']='incorrect';r['reason']=changes[r['source']]['stricter_reason'];changed+=1
    assert changed==8
    budget=[];batch=ROOT/'results/remote/vakra-expansion-v2-complete/runs/vakra-expansion-v2'
    for row in summary['rows']:
        if row['termination']!='input_budget_exceeded':continue
        p=batch/row['source'];assert sha(p)==summary['input_sha256'][row['source']]
        episode=json.loads(p.read_bytes());last=episode['trace'][-1]
        assert last['error_type']=='InputBudgetExceeded'
        match=re.fullmatch(r'Input has (\d+) tokens; registered maximum is (\d+)',last['error']);assert match
        attempted,maximum=map(int,match.groups());assert attempted>maximum==32768
        budget.append(dict(source=row['source'],source_sha256=sha(p),model=row['model'],condition=row['condition'],task_index=row['task_index'],
            successful_generation_calls=sum('reply' in t for t in episode['trace']),recorded_attempted_input_tokens=attempted,limit=maximum))
    assert len(budget)==43 and all('ice_hockey_draft/' in r['source'] for r in budget)
    report=dict(purpose=__doc__,primary=analyze(ann,summary,rules),
        retained_disney_annotation_sensitivity=analyze(strict,summary,rules),changed_answers=8,
        input_budget_failures=budget,
        input_budget_scope='Counters are the saved executor budget checks; not independently retokenized. They retain failures rather than removing resource-limited tasks.',
        evidence_sha256={p.name:sha(p) for p in (ep,ap,cp,dp)},script_sha256=sha(Path(__file__)),
        limits=['Post-completion descriptive uncertainty calculation, not a preregistered hypothesis test.',
                'Resampling is conditional on the four fixed domains and task-pair empirical distributions.',
                'Checkpoints are reported separately; no independent-domain population or multiplicity-adjusted superiority claim.',
                'The eight Disney review changes were already disclosed before full-grid completion; not a bound over all possible adjudications.',
                'No new model runs or prompt changes; one unblinded assistant annotation.'])
    path=output or ev/'vakra_expansion_complete_sensitivity_v1.json'
    with path.open('x',encoding='utf-8') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({variant:[{k:r[k] for k in ('model','original_correct','reminder_correct','gains','losses','difference_percentage_points')}|{'interval':r['conditional_paired_bootstrap']['interval_percentage_points']} for r in report[variant]] for variant in ['primary','retained_disney_annotation_sensitivity']}))
    print(json.dumps({'input_budget_failures':len(budget),'successful_calls_before_failure':dict(Counter(r['successful_generation_calls'] for r in budget)),
        'attempted_input_range':[min(r['recorded_attempted_input_tokens'] for r in budget),max(r['recorded_attempted_input_tokens'] for r in budget)]}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,help='New report path; existing evidence is never overwritten')
    main(parser.parse_args().output)
