"""Conditional task-paired uncertainty for the complete 30B checkpoint audit."""
import hashlib
import json
from pathlib import Path
import random
from scripts.vakra_prompt_uncertainty import quantile


def main():
    source = Path('research/evidence/vakra_qwen30b_answer_annotations_v1.json')
    data = json.loads(source.read_bytes())
    assert data['complete_batch'] and len(data['rows']) == 120
    labels = {(r['domain'], r['uuid'], r['condition']): r['answer_label'] == 'correct'
              for r in data['rows'] if r['interpretation_stratum'] != 'ambiguous'}
    tasks = sorted({(d, u) for d, u, c in labels})
    assert len(tasks) == 55 and len(labels) == 110
    strata = {d:[i for i,(dd,u) in enumerate(tasks) if d == dd] for d,u in tasks}
    delta = [int(labels[d,u,'coverage_check']) - int(labels[d,u,'original']) for d,u in tasks]
    rng = random.Random(20260919)
    draws = []
    for _ in range(10000):
        indices = [rng.choice(group) for group in strata.values() for _ in group]
        draws.append(100 * sum(delta[i] for i in indices) / len(indices))
    report = dict(purpose=__doc__, source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  seed=20260919, resamples=10000, n=55,
                  wins=delta.count(1), losses=delta.count(-1), ties=delta.count(0),
                  difference_percentage_points=100*sum(delta)/55,
                  conditional_bootstrap_percentile_95=[quantile(draws,.025), quantile(draws,.975)],
                  strata={d:len(v) for d,v in strata.items()},
                  leave_one_domain_out=[dict(omitted_domain=d, n=55-len(group),
                      difference_percentage_points=100*sum(x for i,x in enumerate(delta) if i not in group)/(55-len(group)))
                      for d,group in strata.items()],
                  limits='Fixed convenience domains and fixed assistant labels; no annotation, seed or unseen-domain uncertainty. Descriptive, not a population significance claim.')
    with Path('research/evidence/vakra_qwen30b_conditional_uncertainty_v1.json').open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(report,stream,indent=2)
        stream.write('\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
