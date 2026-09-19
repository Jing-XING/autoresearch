"""Descriptive paired counts with a fixed interpretation mask and no failure filtering."""
from collections import Counter


def summarize_review(summary, annotations, rules, *, allow_closed_domain=False):
    """Validate a complete qualitative review; do not assign semantic labels."""
    def require(ok, message):
        if not ok:
            raise ValueError(message)

    partial = allow_closed_domain
    if partial:
        require(summary.get('complete') is False and annotations.get('complete_batch') is False,
                'A closed-domain review must not claim whole-batch completion')
        require(summary.get('closed_domain_complete') is True and annotations.get('complete_domain') is True,
                'Closed-domain execution and annotation must both be complete')
        require(summary['domains'] == [summary.get('closed_domain')] and
                annotations.get('review_scope') == summary['closed_domain'], 'Closed-domain scope mismatch')
    else:
        require(summary.get('complete') is True and annotations.get('complete_batch') is True,
                'Both execution and annotation batches must be complete')
    fields = ('domain', 'uuid', 'model', 'condition')
    key = lambda row: tuple(row[k] for k in fields)
    expected = {key(r): r for r in summary['rows']}
    policies = {(r['domain'], r['uuid']): r for r in rules}
    require(len(expected) == len(summary['rows']), 'Duplicate execution identity')
    require(len(policies) == len(rules), 'Duplicate interpretation identity')
    require(set(summary['domains']) == {r['domain'] for r in rules}, 'Domain mismatch')
    grid = {(d, uid, m, c) for d, uid in policies for m in summary['models']
            for c in ('original', 'coverage_check')}
    require(set(expected) == grid, 'Execution grid differs from fixed task/model/prompt grid')
    reviewed = {}
    for label in annotations['rows']:
        k = key(label)
        require(k in expected and k not in reviewed, 'Unexpected or duplicate annotation')
        row = expected[k]
        rule = policies[k[:2]]
        require(label['task_index'] == row['task_index'] == rule['task_index'], 'Task index mismatch')
        require(label['source'] == row['source'], 'Annotation source mismatch')
        require(label['source_sha256'] == summary['input_sha256'][row['source']], 'Stale source hash')
        require(label['call_policy'] == row['call_policy'] == 'sequential', 'Executor mismatch')
        require(label['interpretation_stratum'] == rule['interpretation_stratum'], 'Changed interpretation mask')
        verdict = label['answer_label']
        require(verdict in ('correct', 'incorrect', 'no_answer', 'ambiguous'), 'Unfinished or unknown label')
        require((verdict == 'ambiguous') == (rule['interpretation_stratum'] == 'ambiguous'),
                'Ambiguous items must retain the frozen label')
        require(isinstance(label['reason'], str) and bool(label['reason'].strip()), 'Missing review reason')
        if row['final_answer'] is None:
            require(verdict in ('no_answer', 'ambiguous'), 'Absent answer cannot be scored as an answer')
        else:
            require(verdict != 'no_answer', 'Present answer cannot be relabeled absent')
        if verdict == 'correct':
            require(row['termination'] == 'agent_finished', 'Correct answer must have completed')
        reviewed[k] = dict(row, answer_label=verdict,
                          interpretation_stratum=rule['interpretation_stratum'])
    require(set(reviewed) == grid, 'Missing annotations')
    groups, pairs = [], []
    for domain in (summary['domains'] if partial else [*summary['domains'], 'all']):
        pool = [r for r in rules if domain == 'all' or r['domain'] == domain]
        scored = [r for r in pool if r['interpretation_stratum'] != 'ambiguous']
        for model in summary['models']:
            for condition in ('original', 'coverage_check'):
                rows = [reviewed[(r['domain'], r['uuid'], model, condition)] for r in pool]
                counts = Counter(r['answer_label'] for r in rows)
                groups.append(dict(domain=domain, model=model, condition=condition,
                    executions=len(rows), scored_tasks=len(scored), ambiguous_tasks=len(pool)-len(scored),
                    correct=counts['correct'], labels=dict(counts),
                    accuracy=counts['correct']/len(scored) if scored else None,
                    final_answers=sum(r['final_answer'] is not None for r in rows),
                    terminations=dict(Counter(r['termination'] for r in rows)),
                    final_at_generation_token_ceiling=sum(r.get('final_at_generation_token_ceiling', False) for r in rows),
                    all_execution_usage={k:sum(r.get('usage', {}).get(k, 0) for r in rows)
                        for k in ('model_calls', 'tool_calls', 'input_tokens', 'output_tokens',
                                  'generation_seconds', 'protocol_errors')}))
            buckets = {k:[] for k in ('gains', 'losses', 'both_correct', 'both_unsuccessful')}
            for rule in scored:
                x, y = [reviewed[(rule['domain'], rule['uuid'], model, c)]['answer_label'] == 'correct'
                        for c in ('original', 'coverage_check')]
                bucket = 'gains' if y and not x else 'losses' if x and not y else 'both_correct' if x else 'both_unsuccessful'
                buckets[bucket].append(dict(domain=rule['domain'], uuid=rule['uuid']))
            pairs.append(dict(domain=domain, model=model, scored_tasks=len(scored), **buckets,
                difference_percentage_points=100*(len(buckets['gains'])-len(buckets['losses']))/len(scored) if scored else None))
    return dict(purpose='Descriptive assistant-authored SQL-interpretation audit; not official or independent human scoring',
                complete_batch=not partial, review_scope=summary.get('closed_domain') if partial else 'full_registered_grid',
                executions=len(expected), distinct_tasks=len(rules), groups=groups, paired=pairs,
                limits=['Failures remain in the fixed scored-task denominators.',
                        'Ambiguous tasks retain their executions and costs but do not enter answer accuracy.',
                        'Task pairs and checkpoints are not independent population samples.',
                        'No evidence-sufficiency or causal mechanism score is inferred from answer correctness.'])
