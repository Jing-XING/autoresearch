"""Task-paired, domain-stratified resampling of existing prompt comparisons.

These are conditional descriptive intervals for fixed observed domains, not
claims about a randomly sampled benchmark population or model-seed variance.
All conditions/models of a task share its resampling multiplicity.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import random


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quantile(values, probability):
    values = sorted(values)
    position = (len(values) - 1) * probability
    lo = int(position)
    hi = min(lo + 1, len(values) - 1)
    return values[lo] + (position - lo) * (values[hi] - values[lo])


def main():
    ev = Path('research/evidence')
    files = [('strict', 'vakra_crossdomain_v1_answer_annotations.json'),
             ('sequential', 'vakra_permissive_v1_answer_annotations.json'),
             ('smollm3', 'vakra_smollm3_v1_answer_annotations.json')]
    labels = {}
    hashes = {}
    for source, filename in files:
        path = ev / filename
        hashes[filename] = sha(path)
        data = json.loads(path.read_bytes())
        assert len(data['rows']) == 240
        for row in data['rows']:
            if row['interpretation_stratum'] == 'ambiguous':
                continue
            policy = row['call_policy'] if source == 'smollm3' else source
            if policy == 'strict':
                policy = 'single'
            key = (row['domain'], row['uuid'], row['model'], policy, row['condition'])
            assert key not in labels
            assert row['answer_label'] in ('correct', 'incorrect', 'no_answer')
            labels[key] = row['answer_label'] == 'correct'
    tasks = sorted({(d, u) for d, u, m, p, c in labels})
    assert len(tasks) == 55
    strata = {d: [i for i, (domain, u) in enumerate(tasks) if domain == d] for d, u in tasks}
    arms = sorted({(m, p) for d, u, m, p, c in labels})
    assert len(arms) == 6
    deltas = {arm: [int(labels[(d, u, *arm, 'coverage_check')]) - int(labels[(d, u, *arm, 'original')])
                    for d, u in tasks] for arm in arms}
    rng = random.Random(20260919)
    draws = {arm: [] for arm in arms}
    for _ in range(10000):
        indices = [rng.choice(group) for group in strata.values() for _ in group]
        for arm in arms:
            draws[arm].append(100 * sum(deltas[arm][i] for i in indices) / len(indices))
    rows = []
    for arm in arms:
        delta = deltas[arm]
        counts = Counter(delta)
        leave_one_out = []
        for omitted in strata:
            values = [delta[i] for i, (domain, u) in enumerate(tasks) if domain != omitted]
            leave_one_out.append({'omitted_domain': omitted, 'n': len(values),
                                  'difference_percentage_points': 100 * sum(values) / len(values)})
        rows.append({'model': arm[0], 'call_policy': arm[1], 'n': len(tasks),
                     'wins': counts[1], 'losses': counts[-1], 'ties': counts[0],
                     'difference_percentage_points': 100 * sum(delta) / len(delta),
                     'conditional_bootstrap_percentile_95': [quantile(draws[arm], .025), quantile(draws[arm], .975)],
                     'leave_one_domain_out': leave_one_out})
    report = {'purpose': __doc__, 'input_sha256': hashes, 'script_sha256': sha(Path(__file__)),
              'seed': 20260919, 'resamples': 10000, 'unit': 'task; all six model/executor arms paired',
              'strata': {k: len(v) for k, v in strata.items()}, 'rows': rows,
              'limits': 'Fixed convenience domains; single deterministic run per cell; assistant labels treated as fixed. Does not cover annotation uncertainty, model-seed variance or unseen-domain variation. No hypothesis-test or population-significance claim.'}
    with (ev / 'vakra_prompt_conditional_uncertainty_v1.json').open('x', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(rows))


if __name__ == '__main__':
    main()
