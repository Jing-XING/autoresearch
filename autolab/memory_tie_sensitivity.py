"""Finite-grid sensitivity; three tie choices are not independent source draws."""
from itertools import combinations
from collections import defaultdict


def describe_tie_sensitivity(rows, registration):
    """Summarize audited paired rows without population inference or best-tie selection."""
    ties = registration['tie_orders']
    tasks = registration['selected_task_ids']
    models = registration['models']
    conditions = registration['memory_conditions']
    if len(set(ties)) != 3 or set(conditions) != {'full_metadata', 'boundary_aware'}:
        raise ValueError('Expected frozen three-choice, two-condition design')
    tickets = {r['task_id']: r['ticket_sha256'] for r in registration['rows']}
    if set(tickets) != set(tasks) or len(tasks) != len(set(tasks)):
        raise ValueError('Task registration coverage differs')
    index = {}
    for row in rows:
        if row['condition'] == 'none':
            continue  # Shared baseline has a separate comparison, never replicated here.
        key = (row['model'], row['tie_order'], row['condition'], row['task_id'])
        if key in index or row['task_id'] not in tickets:
            raise ValueError('Duplicate or unexpected paired cell')
        if row['ticket_sha256'] != tickets[row['task_id']]:
            raise ValueError('Ticket group differs from pre-outcome registration')
        if row['reward'] not in (None, 0, 1):
            raise ValueError('Expected binary official reward or retained error')
        index[key] = int(row['reward'] == 1)
    expected = {(m, t, c, task) for m in models for t in ties for c in conditions for task in tasks}
    if set(index) != expected:
        raise ValueError('Incomplete sensitivity grid')
    groups = sorted(set(tickets.values()))
    if len(groups) < 2:
        raise ValueError('At least two visible-ticket groups required')
    summaries, within_arm = [], []
    for model in models:
        for tie in ties:
            delta = {task: index[model, tie, 'boundary_aware', task] -
                           index[model, tie, 'full_metadata', task] for task in tasks}
            group_effects = []
            for group in groups:
                inside = [v for task, v in delta.items() if tickets[task] == group]
                outside = [v for task, v in delta.items() if tickets[task] != group]
                group_effects.append(dict(ticket_sha256=group, tasks=len(inside),
                    difference=sum(inside) / len(inside),
                    leave_this_ticket_out_difference=sum(outside) / len(outside)))
            summaries.append(dict(model=model, tie_order=tie,
                micro_difference=sum(delta.values()) / len(tasks),
                uniform_ticket_macro_difference=sum(g['difference'] for g in group_effects) / len(groups),
                ticket_groups=group_effects,
                interpretation='Finite registered tasks; macro changes weighting, not the primary estimand'))
        for condition in conditions:
            for left, right in combinations(ties, 2):
                gains = [task for task in tasks if index[model, right, condition, task] > index[model, left, condition, task]]
                losses = [task for task in tasks if index[model, right, condition, task] < index[model, left, condition, task]]
                within_arm.append(dict(model=model, condition=condition, left=left, right=right,
                    gains=gains, losses=losses, changed_tasks=len(gains) + len(losses),
                    success_difference=(len(gains) - len(losses)) / len(tasks)))
    duplicate_groups = defaultdict(list)
    for row in rows:
        if row.get('memory_text_sha256'):
            key = (row['model'], row['task_id'], row['condition'], row['memory_text_sha256'])
            duplicate_groups[key].append(row)
    duplicate_checks = []
    for key, group in sorted(duplicate_groups.items()):
        if len(group) > 1:
            duplicate_checks.append(dict(model=key[0], task_id=key[1], condition=key[2],
                memory_text_sha256=key[3], tie_orders=[r['tie_order'] for r in group],
                identical_model_io=len({r['model_io_sha256'] for r in group}) == 1,
                identical_recorded_rewards=len({r['reward'] for r in group}) == 1))
    return dict(treatment_effects=summaries, within_condition_tie_changes=within_arm,
        duplicate_content_checks=duplicate_checks,
        interpretation='All three preregistered choices reported. No best-choice ranking or pooled independent-sample test.',
        limits='Only five shared ticket/source groups in the intended study. Leave-group-out values are sensitivity diagnostics, not confidence bounds.')
