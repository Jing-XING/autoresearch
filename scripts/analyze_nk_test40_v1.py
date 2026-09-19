"""Audit the complete registered NK adaptation; no full-method superiority claim."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

from autolab.nk_prefix_bank import NKMemoryBank, build_bank
from autolab.nk_prefix_comparator import CONDITIONS
from scripts.analyze_memory_tie_transfer import paired_outcomes, stripped_first_input
from scripts.prepare_memory_restart_analysis_receipt import members

REPO = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(Path(path).read_bytes())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check(ok, message):
    if not ok:
        raise ValueError(message)


def deployment(repo=REPO):
    """Verify original bytes, restart amendment and actually deployed bundle."""
    ev, dep = repo / 'research/evidence', repo / 'results/deploy'
    amendment = read(ev / 'research_queue_restart_amendment_v2.json')
    observed = read(ev / 'research_queue_restart_deployment_v2.json')
    bundle_path = dep / 'research-queue-restart-v2.zip'
    check(sha(bundle_path) == amendment['bundle_sha256'] == observed['bundle_sha256'], 'Restart bundle differs')
    bundle = members(bundle_path)
    check(json.loads(bundle['restart_amendment.json']) == {
        k: v for k, v in amendment.items() if k not in ('bundle_sha256', 'bundle_bytes', 'bundle_members')},
        'Bundled amendment differs')
    result, archives = {}, {}
    for batch, old_receipt, registration in (
        ('nk-prefix-curation-v2', 'nk_prefix_curation_deployment_v1.json', 'nk_prefix_curation_registration_v1.json'),
        ('tau-nk-test40-v2', 'nk_test40_deployment_v1.json', 'nk_test40_registration_v1.json')):
        matches = [r for r in amendment['revisions'] if r['batch'] == batch]
        check(len(matches) == 1, 'Missing unique restart amendment')
        r = matches[0]
        old_path, new_path = [dep / (r[k] + '.zip') for k in ('original_revision', 'revision')]
        check(not r['changed_existing_files'], 'Registered inference changed')
        check(sha(old_path) == r['original_archive_sha256'] == read(ev / old_receipt)['archive_sha256'], 'Original archive differs')
        check(sha(new_path) == r['archive_sha256'], 'Restart archive differs')
        old, new = members(old_path), members(new_path)
        extra = 'scripts/restart_registered_queue_v2.py'
        check(set(new) == set(old) | {extra} and all(new[k] == v for k, v in old.items()), 'Restart changed original bytes')
        check(hashlib.sha256(new[extra]).hexdigest() == r['supervisor_sha256'], 'Supervisor differs')
        check(new['protocol/registration.json'] == (ev / registration).read_bytes(), 'Registration differs')
        check(all(hashlib.sha256(new[k]).hexdigest() == v for k, v in r['preserved_protocol_files'].items()), 'Protocol differs')
        check(all(bundle[r['revision'] + '/' + k] == v for k, v in new.items()), 'Bundle and standalone archive differ')
        pre = [p for p in observed['remote_preflights'] if p['revision'] == r['revision']]
        processes = [p for p in observed['processes'] if p['batch'] == batch]
        check(len(processes) == 1, 'Missing deployment process evidence')
        if batch == 'tau-nk-test40-v2':
            check(len(pre) == 1 and pre[0]['exit_code'] == 0, 'Missing target preflight evidence')
        else:
            check(not pre, 'Unexpected curation restart preflight record')
        result[batch] = dict(archive_sha256=sha(new_path), original_sha256=sha(old_path),
                            original_members_preserved=len(old), only_added_member=extra,
                            registration_sha256=sha(ev / registration), supervisor_sha256=r['supervisor_sha256'],
                            restart_preflight_recorded=bool(pre))
        archives[batch] = new
    target = archives['tau-nk-test40-v2']
    check(target['protocol/selection.json'] == (ev / 'nk_prefix_target_selection_v1.json').read_bytes(), 'Selection differs')
    check(target['protocol/curation_registration.json'] == (ev / 'nk_prefix_curation_registration_v1.json').read_bytes(), 'Curation registration differs')
    reg = read(ev / 'nk_test40_registration_v1.json')
    for name, digest in reg['source_files_sha256'].items():
        check(hashlib.sha256(target[name]).hexdigest() == digest, 'Target source archive mismatch: ' + name)
        # Only imported modules are required locally; original supervisor stays in its ZIP.
        if name.startswith('autolab/'):
            check(sha(repo / name) == digest, 'Local analysis dependency differs: ' + name)
    return {'revisions': result, 'bundle_sha256': sha(bundle_path),
            'amendment_sha256': sha(ev / 'research_queue_restart_amendment_v2.json'),
            'deployment_sha256': sha(ev / 'research_queue_restart_deployment_v2.json')}, archives


def usage_add(total, usage):
    for key in ('input_tokens', 'output_tokens', 'elapsed_seconds'):
        value = usage.get(key)
        check(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0,
              'Invalid observed generation usage')
        total[key] += value


def analyze_targets(root, reg_path, selection_path, bank_path, batch='tau-nk-test40-v2'):
    reg, selection, bank_value = map(read, (reg_path, selection_path, bank_path))
    grid = read(root / 'grid_manifest.json')
    check(grid['status'] == 'complete' and grid['batch'] == batch and grid['registration'] == reg,
          'Refuse incomplete, changed or wrong target grid')
    check(reg['registered_episodes'] == grid['registered_episodes'] == 160 and reg['target_count'] == 40,
          'Target denominator changed')
    check(reg['conditions'] == list(CONDITIONS) and set(reg['models']) == {'qwen3', 'qwen25'}, 'Target arms changed')
    check(sha(selection_path) == reg['selection_sha256'], 'Target selection changed')
    check(bank_value['curation_registration_sha256'] == reg['curation_registration_sha256'] and
          bank_value['preparation_manifest_sha256'] == selection['preparation_manifest_sha256'], 'Bank provenance changed')
    bank = NKMemoryBank(bank_value)
    choices = {r['task_id']: r for r in selection['rows']}
    ids = [r['task_id'] for r in selection['rows']]
    check(len(ids) == len(choices) == 40, 'Task selection coverage changed')
    bank.assert_disjoint(ids)
    check(sorted(bank.by_id) == selection['selected_source_ids'], 'Eligible source pool changed')
    expected = {(c, m, s) for c in CONDITIONS for m in reg['models'] for s in (0, 1)}
    workers = [(w['condition'], w['model'], w['shard']) for w in grid['workers']]
    check(len(workers) == 8 and set(workers) == expected and all(w.get('exit_code') == 0 for w in grid['workers']), 'Target workers incomplete')
    folders = {root / c / m / f'shard-{s}' for c, m, s in expected}
    check(set(root.glob('*/*/shard-*/manifest.json')) == {f / 'manifest.json' for f in folders}, 'Unexpected worker manifest')
    rows, inputs, task_hashes, common = [], {}, {}, None
    for condition, model, shard in sorted(expected):
        folder = root / condition / model / f'shard-{shard}'
        manifest = read(folder / 'manifest.json')
        expected_manifest = dict(batch=reg['batch'], model=model, task_split='test', all_task_ids=ids,
            selected_task_ids=ids[shard::2], shard=shard, shards=2, condition=condition,
            registration_sha256=sha(reg_path), selection_sha256=sha(selection_path), memory_bank_sha256=sha(bank_path),
            seed=20260919, decoder='greedy_native_template_tool_prefix', supplied_prefix='<tool_call>\n',
            max_new_tokens=512, max_steps=60, max_errors=5, source_sha256=reg['source_files_sha256'],
            model_files_sha256=reg['model_files_sha256'][model])
        check(all(manifest[k] == v for k, v in expected_manifest.items()), 'Target manifest changed')
        config = read(folder / 'config.json')
        check(all(config[k] == v for k, v in dict(domain='telecom', max_steps=60, max_errors=5,
              seed=20260919, enforce_communication_protocol=True).items()), 'Runtime config changed')
        invariant = {k: manifest[k] for k in ('tau_source_manifest_sha256', 'packages', 'source_sha256')}
        check(common is None or common == invariant, 'Target runtime changed across cells')
        common = invariant
        check(set(manifest['task_sha256']) == set(ids[shard::2]), 'Missing task fingerprints')
        local, files = [], set()
        for index, task_id in enumerate(ids[shard::2]):
            stem = f'case-{index:03d}'
            files.update((stem + '-status.json', stem + '-model-audit.json'))
            status, audit = [read(folder / (stem + suffix)) for suffix in ('-status.json', '-model-audit.json')]
            check(status['task_id'] == audit['task_id'] == task_id and status['model_calls'] == len(audit['calls']), 'Task status/audit mismatch')
            check(status['reward'] in (None, 0, 1), 'Nonbinary official reward')
            digest = manifest['task_sha256'][task_id]
            check(task_id not in task_hashes or task_hashes[task_id] == digest, 'Task content changed')
            task_hashes[task_id] = digest
            if status['reward'] is not None:
                files.add(stem + '.json')
                sim = read(folder / (stem + '.json'))
                check(sim['task_id'] == task_id and sim['reward_info']['reward'] == status['reward'] and
                      sim['termination_reason'] == status['termination'], 'Official result differs from status')
            else:
                check(bool(status.get('error_type')), 'Missing recorded execution error')
            choice = choices[task_id]['source_choice']
            source = bank.by_id[choice['record_id']]
            memory = source['memories'][condition]
            curation_status = source['curation'][condition]['status']
            usage, errors = Counter(), []
            for step, call in enumerate(audit['calls']):
                check(call['step'] == step and hashlib.sha256(json.dumps(call['input'], sort_keys=True).encode()).hexdigest() == call['input_sha256'], 'Model input integrity failure')
                usage_add(usage, call['reply'])
                if call.get('protocol_error'):
                    errors.append(call['protocol_error'])
            if audit['calls']:
                first = audit['calls'][0]
                selected = first['memory_selection']
                expected_selection = {**choice, 'condition': condition, 'curation_status': curation_status,
                                      'memory_sha256': hashlib.sha256(memory.encode()).hexdigest()}
                check(selected == expected_selection, 'Observed source choice or curation quality differs')
                clean = stripped_first_input(first, condition, memory)
                check(task_id not in inputs or clean == inputs[task_id], 'Initial policy, task or tools changed')
                inputs[task_id] = clean
            rows.append(dict(model=model, condition=condition, task_id=task_id,
                reward=status['reward'], error_type=status.get('error_type'), termination=status.get('termination'),
                model_calls=status['model_calls'], initial_input_observed=bool(audit['calls']),
                usage=dict(usage), protocol_errors=errors, source_record_id=choice['record_id'],
                curation_status=curation_status, empty_memory=not memory,
                memory_sha256=hashlib.sha256(memory.encode()).hexdigest(), ticket_sha256=choices[task_id]['ticket_sha256']))
            local.append(status)
        check({p.name for p in folder.glob('case-*.json')} == files, 'Extra or missing case artifact')
        summary = read(folder / 'summary.json')
        check(summary['rows'] == local and summary['n'] == 20 and summary['successes'] == sum(r['reward'] == 1 for r in local)
              and summary['errors'] == sum(r['reward'] is None for r in local), 'Target summary mismatch')
    check(len(rows) == 160, 'Incomplete target outcomes')
    control = [r for r in rows if r['condition'] == CONDITIONS[0]]
    treated = [r for r in rows if r['condition'] == CONDITIONS[1]]
    paired = paired_outcomes(treated, control)
    groups, sensitivity = [], []
    for model in reg['models']:
        for condition in CONDITIONS:
            subset = [r for r in rows if (r['model'], r['condition']) == (model, condition)]
            cost = Counter()
            for row in subset:
                cost.update(row['usage'])
            groups.append(dict(model=model, condition=condition, tasks=len(subset), successes=sum(r['reward'] == 1 for r in subset),
                errors=sum(r['reward'] is None for r in subset), protocol_error_episodes=sum(bool(r['protocol_errors']) for r in subset),
                empty_memory_episodes=sum(r['empty_memory'] for r in subset), distinct_memory_texts_including_empty=len({r['memory_sha256'] for r in subset}),
                curation_status_by_target=dict(Counter(r['curation_status'] for r in subset)), source_reuse=dict(Counter(r['source_record_id'] for r in subset)),
                target_generation_usage=dict(cost)))
        a = {r['task_id']: r for r in treated if r['model'] == model}
        b = {r['task_id']: r for r in control if r['model'] == model}
        delta = {uid: int(a[uid]['reward'] == 1) - int(b[uid]['reward'] == 1) for uid in ids}
        by_ticket = []
        tickets = sorted({r['ticket_sha256'] for r in a.values()})
        for ticket in tickets:
            inside = [uid for uid in ids if a[uid]['ticket_sha256'] == ticket]
            outside = [uid for uid in ids if uid not in inside]
            check(bool(outside), 'Only one visible-ticket group')
            by_ticket.append(dict(ticket_sha256=ticket, tasks=len(inside),
                source_ids=sorted({a[uid]['source_record_id'] for uid in inside}),
                paired=paired_outcomes([a[uid] for uid in inside], [b[uid] for uid in inside])[0],
                leave_group_out_difference=sum(delta[uid] for uid in outside) / len(outside)))
        sensitivity.append(dict(model=model, task_equal_difference=sum(delta.values()) / len(ids),
            group_equal_difference=sum(g['paired']['success_difference'] for g in by_ticket) / len(by_ticket),
            visible_ticket_groups=by_ticket))
    return dict(complete=True, registered_episodes=160, distinct_tasks=40, rows=rows, groups=groups,
        primary_boundary_minus_schema=paired, descriptive_group_sensitivity=sensitivity,
        first_input_observed_episodes=sum(r['initial_input_observed'] for r in rows),
        no_first_input_episodes=[{k:r[k] for k in ('model','condition','task_id','error_type')} for r in rows if not r['initial_input_observed']],
        configuration=common, registration_sha256=sha(reg_path), selection_sha256=sha(selection_path), bank_sha256=sha(bank_path),
        raw_sha256={p.relative_to(root).as_posix():sha(p) for p in sorted(root.rglob('*.json'))})


def analyze_curation(root, prepared, source_bank, reg_path, bank_path):
    grid = read(root / 'grid_manifest.json')
    check(grid['status'] == 'complete' and grid['batch'] == 'nk-prefix-curation-v2', 'Curation is not complete')
    check(len(grid['workers']) == 4 and all(w.get('exit_code') == 0 for w in grid['workers'])
          and {w['gpu'] for w in grid['workers']} == set(range(4)), 'Curation worker coverage changed')
    check(grid['expected_sources'] == 70 and grid['expected_curations'] == 140, 'Curation denominator changed')
    rebuilt = build_bank(prepared, root, source_bank, reg_path)
    # The builder uses integer shard keys, which JSON serialization makes strings.
    check(json.loads(json.dumps(rebuilt, allow_nan=False)) == read(bank_path), 'Saved bank differs from raw curation reconstruction')
    check(len(rebuilt['records']) == 70, 'Eligible curation pool changed')
    all_counts = Counter()
    for shard in range(4):
        folder = root / f'shard-{shard}'
        manifest = read(folder / 'manifest.json')
        expected_files = {'manifest.json', 'summary.json'} | {
            f'{uid}-{c}.json' for uid in manifest['selected_record_ids'] for c in CONDITIONS}
        check({p.name for p in folder.glob('*.json')} == expected_files, 'Unexpected curation output')
        summary = read(folder / 'summary.json')
        counts = Counter(r['status'] for r in summary['rows'])
        for key, status in [('valid', 'valid_memory'), ('invalid', 'invalid_memory'), ('generation_errors', 'generation_error')]:
            check(summary[key] == counts[status], 'Curation summary count differs')
            all_counts[key] += counts[status]
    check(dict(all_counts) == grid['outcomes'], 'Curation grid summary differs')
    groups = []
    for condition in CONDITIONS:
        statuses, cost, validation_errors, runtime_errors = Counter(), Counter(), Counter(), Counter()
        observed = 0
        for record in rebuilt['records']:
            c = record['curation'][condition]
            statuses[c['status']] += 1
            if c['status'] != 'generation_error':
                usage_add(cost, c['usage'])
                observed += 1
        for path in root.glob(f'shard-*/*-{condition}.json'):
            value = read(path)
            validation_errors.update(value.get('validation_errors', []))
            if value.get('error_type'):
                runtime_errors[value['error_type']] += 1
        groups.append(dict(condition=condition, sources=70, status_counts=dict(statuses),
            observed_generation_usage=dict(cost), replies_with_usage=observed,
            generation_errors_without_usage=70-observed, validation_errors=dict(validation_errors), runtime_errors=dict(runtime_errors)))
    return dict(sources=70, curations=140, groups=groups, bank_reconstructed=True,
                raw_sha256={p.relative_to(root).as_posix():sha(p) for p in sorted(root.rglob('*.json'))})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('target-root', 'curation-root', 'prepared', 'bank', 'source-bank', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    provenance, archives = deployment()
    # This check accesses only the grid status before any curation text or target outcome.
    check(read(args.target_root / 'grid_manifest.json')['status'] == 'complete', 'Target collection still open')
    prepared_files = {k[len('prepared/'):]:v for k,v in archives['nk-prefix-curation-v2'].items() if k.startswith('prepared/')}
    check(set(prepared_files) == {p.relative_to(args.prepared).as_posix() for p in args.prepared.rglob('*') if p.is_file()}, 'Prepared input inventory changed')
    check(all((args.prepared / k).read_bytes() == v for k,v in prepared_files.items()), 'Prepared input bytes changed')
    ev = REPO / 'research/evidence'
    curation = analyze_curation(args.curation_root, args.prepared, args.source_bank,
                               ev / 'nk_prefix_curation_registration_v1.json', args.bank)
    result = analyze_targets(args.target_root, ev / 'nk_test40_registration_v1.json',
                             ev / 'nk_prefix_target_selection_v1.json', args.bank)
    result.update(deployment=provenance, curation=curation,
        analysis_source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__), REPO / 'scripts/analyze_memory_tie_transfer.py',
            REPO / 'scripts/prepare_memory_restart_analysis_receipt.py', REPO / 'autolab/analyze_memory_transfer.py']},
        limits=['NK-schema adaptation, not a reproduction of full Negative Knowledge or a new memory method.',
                'Single greedy curator realization. Source validity is syntactic/schema validity, not semantic grounding.',
                'Errors and invalid selected memories remain in the registered denominator. Empty memory retains its wrapper.',
                'Shared sources and repeated target tasks are dependent; group weighting is descriptive, not population uncertainty.',
                'Curation cost charged once per bank; generation errors may lack usage. Model loading and source collection excluded.',
                'No cross-study superiority or no-memory comparison is computed by this analysis.'])
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(result['groups']))


if __name__ == '__main__':
    main()
