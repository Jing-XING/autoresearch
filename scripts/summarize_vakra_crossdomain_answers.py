"""Validate every qualitative label and retain fixed denominators and pairing."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--summary', type=Path, required=True)
    p.add_argument('--annotations', type=Path, required=True)
    p.add_argument('--evidence', type=Path, default=Path('research/evidence'))
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    sp = a.summary
    cp = a.evidence / 'vakra_crossdomain_sql_cards_v1.json'
    pp = a.evidence / 'vakra_crossdomain_answer_audit_policy_v1.json'
    summary, labels, policy = (json.loads(x.read_bytes()) for x in (sp, a.annotations, pp))
    for field, path in [('execution_summary_sha256', sp), ('audit_cards_sha256', cp), ('audit_policy_sha256', pp)]:
        assert labels[field] == sha(path), field
    assert policy['sql_cards_sha256'] == sha(cp)
    expected = {(r['domain'], r['condition'], r['model'], r['uuid']): r for r in summary['rows']}
    rules = {(r['domain'], r['uuid']): r for r in policy['rows']}
    assert len(expected) == 240 and len(rules) == 60
    observed = {}
    for r in labels['rows']:
        key = (r['domain'], r['condition'], r['model'], r['uuid'])
        assert key in expected and key not in observed, key
        original = expected[key]
        rule = rules[(r['domain'], r['uuid'])]
        assert r['task_index'] == rule['task_index']
        assert r['interpretation_stratum'] == rule['interpretation_stratum']
        assert r['answer_label'] in ('correct', 'incorrect', 'no_answer', 'ambiguous')
        assert (r['answer_label'] == 'ambiguous') == (rule['interpretation_stratum'] == 'ambiguous')
        assert r['reference_compatibility'] in ('compatible', 'incompatible', 'no_answer', 'unresolved')
        assert isinstance(r['reason'], str) and r['reason'].strip()
        if original['final_answer'] is None:
            assert r['answer_label'] in ('no_answer', 'ambiguous')
            assert r['reference_compatibility'] == 'no_answer'
        else:
            assert r['answer_label'] != 'no_answer'
            assert r['reference_compatibility'] != 'no_answer'
        if r['answer_label'] == 'correct':
            assert original['termination'] == 'agent_finished'
        assert r['source'] == original['source']
        source = (a.root / r['source']).resolve()
        assert source.is_relative_to(a.root.resolve())
        assert sha(source) == r['source_sha256'] == summary['input_sha256'][r['source']]
        observed[key] = r
    assert set(expected) == set(observed)
    groups, paired = [], []
    domains = summary['domains']
    for domain in [*domains, 'all']:
        pool = [r for r in rules.values() if domain == 'all' or r['domain'] == domain]
        clear = [r for r in pool if r['interpretation_stratum'] != 'ambiguous']
        for model in ('qwen3', 'qwen25'):
            for condition in ('original', 'coverage_check'):
                rows = [observed[(r['domain'], condition, model, r['uuid'])] for r in pool]
                counts = Counter(r['answer_label'] for r in rows)
                groups.append({'domain': domain, 'model': model, 'condition': condition,
                               'executions': len(rows), 'clear_interpretation_n': len(clear),
                               'correct': counts['correct'], 'labels': dict(counts),
                               'reference_compatibility': dict(Counter(r['reference_compatibility'] for r in rows))})
            wins, losses, same_correct, same_failed = [], [], [], []
            for rule in clear:
                x, y = (observed[(rule['domain'], c, model, rule['uuid'])]['answer_label'] == 'correct'
                        for c in ('original', 'coverage_check'))
                target = wins if y and not x else losses if x and not y else same_correct if x else same_failed
                target.append({'domain': rule['domain'], 'uuid': rule['uuid']})
            paired.append({'domain': domain, 'model': model, 'n': len(clear), 'wins': wins,
                           'losses': losses, 'same_correct': same_correct, 'same_failed': same_failed,
                           'difference_percentage_points': 100 * (len(wins) - len(losses)) / len(clear)})
    assert all(r['clear_interpretation_n'] == 55 for r in groups if r['domain'] == 'all')
    special = []
    for rule in rules.values():
        if rule['verified_reference_conflict'] or rule['task_local_initial_scope_witness'] or rule['ambiguity']:
            special.append({'policy': rule, 'outcomes': [observed[(rule['domain'], c, m, rule['uuid'])]
                            for m in ('qwen3', 'qwen25') for c in ('original', 'coverage_check')]})
    result = {'purpose': 'descriptive assistant-authored SQL audit, not official score or independent human labels',
              'annotations_sha256': sha(a.annotations), 'distinct_tasks': 60, 'executions': 240,
              'groups': groups, 'paired': paired, 'special_cases': special,
              'inference_limit': 'deterministically selected small databases; task-paired executions; no population significance claim'}
    with a.output.open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps({'groups': groups, 'paired_counts': [
        {k: len(v) if isinstance(v, list) else v for k, v in r.items()} for r in paired]}))


if __name__ == '__main__':
    main()
