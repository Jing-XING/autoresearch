"""Join complete third-model execution and literal answer reviews."""
from collections import Counter
import hashlib
import json
from pathlib import Path


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ev = Path('research/evidence')
    sp = ev / 'vakra_smollm3_v1_execution_summary.json'
    ap = ev / 'vakra_smollm3_v1_answer_annotations.json'
    summary, annotations = [json.loads(p.read_bytes()) for p in (sp, ap)]
    assert summary['complete'] and annotations['complete_batch']
    assert annotations['execution_summary_sha256'] == sha(sp)
    by_source = {r['source']: r for r in annotations['rows']}
    assert len(by_source) == len(summary['rows']) == 240
    rows = []
    for execution in summary['rows']:
        label = by_source[execution['source']]
        assert label['source_sha256'] == summary['input_sha256'][execution['source']]
        assert all(label[k] == execution[k] for k in ('domain', 'uuid', 'call_policy', 'condition'))
        assert label['answer_label'] in ('correct', 'incorrect', 'ambiguous')
        assert label['answer_label'] != 'correct' or execution['final_answer'] is not None
        rows.append(dict(execution, **{k: label[k] for k in ('answer_label', 'interpretation_stratum', 'qualified_answer_sensitivity')}))
    groups = []
    for domain in ['all'] + summary['domains']:
        for policy in ('single', 'sequential'):
            for condition in ('original', 'coverage_check'):
                pool = [r for r in rows if r['call_policy'] == policy and r['condition'] == condition
                        and (domain == 'all' or r['domain'] == domain)]
                included = [r for r in pool if r['interpretation_stratum'] != 'ambiguous']
                groups.append({'domain': domain, 'call_policy': policy, 'condition': condition,
                               'all_n': len(pool), 'sql_subtotal_n': len(included),
                               'correct': sum(r['answer_label'] == 'correct' for r in included),
                               'correct_excluding_qualified_answers': sum(r['answer_label'] == 'correct' and not r['qualified_answer_sensitivity'] for r in included),
                               'final_answers': sum(r['final_answer'] is not None for r in pool),
                               'final_at_token_ceiling': sum(r['final_at_generation_token_ceiling'] for r in pool),
                               'terminations': dict(Counter(r['termination'] for r in pool)),
                               'usage': {k: sum(r['usage'].get(k, 0) for r in pool) for k in
                                         ('model_calls', 'tool_calls', 'input_tokens', 'output_tokens', 'generation_seconds', 'protocol_errors')}})
    paired = []
    key = {(r['domain'], r['uuid'], r['call_policy'], r['condition']): r for r in rows}
    for policy in ('single', 'sequential'):
        wins, losses, ties = [], [], []
        for r in rows:
            if r['call_policy'] != policy or r['condition'] != 'original' or r['interpretation_stratum'] == 'ambiguous':
                continue
            other = key[(r['domain'], r['uuid'], policy, 'coverage_check')]
            x, y = r['answer_label'] == 'correct', other['answer_label'] == 'correct'
            target = wins if y and not x else losses if x and not y else ties
            target.append({'domain': r['domain'], 'task_index': r['task_index']})
        assert len(wins) + len(losses) + len(ties) == 55
        paired.append({'call_policy': policy, 'wins': wins, 'losses': losses, 'ties': len(ties)})
    report = {'purpose': __doc__, 'episodes': 240, 'distinct_tasks': 60,
              'execution_summary_sha256': sha(sp), 'annotations_sha256': sha(ap),
              'groups': groups, 'prompt_pairs': paired,
              'answer_labels': dict(Counter(r['answer_label'] for r in rows)),
              'limits': 'Assistant qualitative SQL audit, not official scoring. Two USA predictions are explicitly qualified; both credited and excluded sensitivity totals provided. Known tasks, single run per cell, native-profile/resource-specific floor performance, not a general model ranking.'}
    with (ev / 'vakra_smollm3_v1_answer_summary.json').open('x', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    print(json.dumps({'groups': [g for g in groups if g['domain'] == 'all'], 'pairs': paired,
                      'labels': report['answer_labels']}))


if __name__ == '__main__':
    main()
