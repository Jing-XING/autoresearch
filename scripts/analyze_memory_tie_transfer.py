"""Audit the entire frozen 560-episode memory study before paired reporting."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import zipfile

from autolab.analyze_memory_transfer import paired_contrast
from autolab.memory_tie_sensitivity import describe_tie_sensitivity

WRAPPER = (
    "\n\nPrior experience from a different task follows as quoted data. "
    "It may be incomplete or inapplicable. The current policy, ticket "
    "and observed tool results take precedence. Do not copy source "
    "entity identifiers without checking the current environment.\n"
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def stripped_first_input(call, condition, expected_memory):
    messages = json.loads(json.dumps(call['input']))
    if not messages or messages[0]['role'] != 'system':
        raise ValueError('Missing initial system policy')
    if condition != 'none':
        suffix = WRAPPER + json.dumps({'prior_experience': expected_memory}, ensure_ascii=False)
        if not messages[0]['content'].endswith(suffix):
            raise ValueError('Model input does not contain the exact frozen lesson and wrapper')
        messages[0]['content'] = messages[0]['content'][:-len(suffix)]
    return {'messages': messages, 'tools': call['tools']}


def analyze(root, registration_path, bank_path, code_zip, deployment_path):
    reg, bank, deployment = map(read, (registration_path, bank_path, deployment_path))
    grid = read(root / 'grid_manifest.json')
    if grid['status'] != 'complete' or len(grid['workers']) != 28 or any(w.get('exit_code') != 0 for w in grid['workers']):
        raise ValueError('Refuse incomplete or failed worker grid')
    if grid['selection'] != reg or reg['registered_episodes'] != 560:
        raise ValueError('Registration differs from frozen grid')
    if sha(code_zip) != deployment['source_archive_sha256']:
        raise ValueError('Deployment code ZIP mismatch')
    if sha(bank_path) != reg['source_bank_sha256']:
        raise ValueError('Memory bank mismatch')
    ids = reg['selected_task_ids']
    if len(ids) != 40 or len(set(ids)) != 40 or set(ids) & set(bank['source_task_ids']):
        raise ValueError('Target coverage or source overlap violation')
    selected = {r['task_id']: r for r in reg['rows']}
    records = {r['record_id']: r for r in bank['records']}
    arms = [('record_id', 'none')] + [(t, c) for t in reg['tie_orders'] for c in reg['memory_conditions']]
    expected_workers = {(t, c, m, s) for t, c in arms for m in reg['models'] for s in (0, 1)}
    actual_workers = [(w['tie_order'], w['condition'], w['model'], w['shard']) for w in grid['workers']]
    if len(set(actual_workers)) != 28 or set(actual_workers) != expected_workers:
        raise ValueError('Missing, repeated or unexpected worker')
    source_hashes = {}
    with zipfile.ZipFile(code_zip) as z:
        for name in z.namelist():
            if name.startswith('autolab/') and name.endswith('.py'):
                source_hashes[Path(name).name] = hashlib.sha256(z.read(name)).hexdigest()
    rows, fingerprints, runtimes, task_hashes, initial_inputs = [], {}, {}, {}, {}
    common = None
    for tie, condition, model, shard in sorted(expected_workers):
        folder = root / tie / condition / model / f'shard-{shard}'
        manifest = read(folder / 'manifest.json')
        expected_manifest = dict(batch=reg['batch'], model=model, task_split='test', all_task_ids=ids,
            selected_task_ids=ids[shard::2], shard=shard, shards=2, condition=condition, tie_order=tie,
            registration_sha256=sha(registration_path), memory_bank_sha256=sha(bank_path),
            seed=20260919, decoder='greedy_native_template_tool_prefix', supplied_prefix='<tool_call>\n',
            max_new_tokens=512, max_steps=60, max_errors=5)
        if any(manifest[k] != v for k, v in expected_manifest.items()):
            raise ValueError(f'Manifest violates registration: {folder}')
        if any(source_hashes.get(k) != v for k, v in manifest['source_sha256'].items()):
            raise ValueError('Recorded source differs from deployed ZIP')
        config = read(folder / 'config.json')
        if any(config[k] != v for k, v in dict(domain='telecom', max_steps=60, max_errors=5,
                seed=20260919, enforce_communication_protocol=True).items()):
            raise ValueError('Official runtime config changed')
        invariant = {k: manifest[k] for k in ('source_sha256', 'tau_source_manifest_sha256', 'packages')}
        if common is not None and invariant != common:
            raise ValueError('Code/runtime changes across cells')
        common = invariant
        weights = manifest['model_files_sha256']
        if model in runtimes and runtimes[model] != weights:
            raise ValueError('Model weights change across cells')
        runtimes[model] = weights
        if set(manifest['task_sha256']) != set(ids[shard::2]):
            raise ValueError('Incomplete task fingerprints')
        local_rows = []
        for index, task_id in enumerate(ids[shard::2]):
            digest = manifest['task_sha256'][task_id]
            if task_id in task_hashes and task_hashes[task_id] != digest:
                raise ValueError('Task content changed across cells')
            task_hashes[task_id] = digest
            status = read(folder / f'case-{index:03d}-status.json')
            audit = read(folder / f'case-{index:03d}-model-audit.json')
            if status['task_id'] != task_id or audit['task_id'] != task_id or status['model_calls'] != len(audit['calls']):
                raise ValueError('Task/audit/status disagreement')
            if status['reward'] not in (None, 0, 1):
                raise ValueError('Unexpected nonbinary reward')
            simulation_path = folder / f'case-{index:03d}.json'
            if status['reward'] is not None:
                simulation = read(simulation_path)
                if simulation['task_id'] != task_id or simulation['reward_info']['reward'] != status['reward'] or simulation['termination_reason'] != status['termination']:
                    raise ValueError('Official simulation/status disagreement')
            elif not status.get('error_type'):
                raise ValueError('Null reward lacks retained error')
            usage, protocol_errors = Counter(), []
            for step, call in enumerate(audit['calls']):
                if call['step'] != step or hashlib.sha256(json.dumps(call['input'], sort_keys=True).encode()).hexdigest() != call['input_sha256']:
                    raise ValueError('Model-input integrity failure')
                usage.update({k: call['reply'][k] for k in ('input_tokens', 'output_tokens', 'elapsed_seconds')})
                if call.get('protocol_error'):
                    protocol_errors.append(call['protocol_error'])
            chosen = selected[task_id]['choices'][tie] if condition != 'none' else None
            if audit['calls']:
                first = audit['calls'][0]
                memory = None
                if chosen:
                    selection = first['memory_selection']
                    if selection['condition'] != condition or selection['tie_order'] != tie or any(selection[k] != v for k, v in chosen.items()):
                        raise ValueError('Observed source choice differs from registration')
                    memory = records[chosen['record_id']]['memories'][condition]
                elif 'memory_selection' in first:
                    raise ValueError('Memory leaked into no-memory control')
                clean_input = stripped_first_input(first, condition, memory)
                if task_id in initial_inputs and initial_inputs[task_id] != clean_input:
                    raise ValueError('Initial policy, task or ordered tool schemas changed across cells')
                initial_inputs[task_id] = clean_input
            row = {'model': model, 'task_id': task_id, 'tie_order': tie, 'condition': condition,
                   'reward': status['reward'], 'error_type': status.get('error_type'),
                   'termination': status.get('termination'), 'model_calls': status['model_calls'],
                   'usage': dict(usage), 'protocol_errors': protocol_errors,
                   'source_record_id': chosen['record_id'] if chosen else None,
                   'ticket_sha256': selected[task_id]['ticket_sha256']}
            rows.append(row)
            local_rows.append(status)
        summary = read(folder / 'summary.json')
        if summary['rows'] != local_rows or summary['n'] != 20 or summary['successes'] != sum(r['reward'] == 1 for r in local_rows) or summary['errors'] != sum(r['reward'] is None for r in local_rows):
            raise ValueError('Worker summary disagreement')
        for path in folder.glob('*.json'):
            fingerprints[path.relative_to(root).as_posix()] = sha(path)
    if len(rows) != 560:
        raise ValueError('Incomplete registered episode set')
    groups, contrasts, ticket_groups = [], {}, []
    for tie, condition in arms:
        for model in reg['models']:
            subset = [r for r in rows if (r['tie_order'], r['condition'], r['model']) == (tie, condition, model)]
            usage = Counter()
            for row in subset:
                usage.update(row['usage'])
            groups.append(dict(tie_order=tie, condition=condition, model=model, tasks=len(subset),
                successes=sum(r['reward'] == 1 for r in subset), errors=sum(r['reward'] is None for r in subset),
                protocol_error_episodes=sum(bool(r['protocol_errors']) for r in subset), usage=dict(usage),
                source_reuse=dict(Counter(r['source_record_id'] for r in subset if r['source_record_id']))))
    for tie in reg['tie_orders']:
        full = [r for r in rows if r['tie_order'] == tie and r['condition'] == 'full_metadata']
        boundary = [r for r in rows if r['tie_order'] == tie and r['condition'] == 'boundary_aware']
        label = 'primary' if tie == 'record_id' else 'prespecified_sensitivity'
        contrasts[tie + '_boundary_minus_full'] = {'role': label, 'paired': paired_contrast(boundary, full)}
        baseline = [r for r in rows if r['condition'] == 'none']
        for condition, subset in [('full_metadata', full), ('boundary_aware', boundary)]:
            contrasts[tie + '_' + condition + '_minus_none'] = {'role': 'secondary_shared_baseline', 'paired': paired_contrast(subset, baseline)}
        for ticket in sorted({r['ticket_sha256'] for r in rows}):
            a = [r for r in boundary if r['ticket_sha256'] == ticket]
            b = [r for r in full if r['ticket_sha256'] == ticket]
            ticket_groups.append({'tie_order': tie, 'ticket_sha256': ticket, 'paired': paired_contrast(a, b)})
    curation = {}
    for condition in reg['memory_conditions']:
        total = Counter()
        for record in bank['records']:
            total.update(record['curation_usage'][condition])
        curation[condition] = dict(total)
    return dict(complete=True, registered_episodes=560, distinct_targets=40,
        analysis_source_sha256={str(p.relative_to(Path(__file__).resolve().parents[1])): sha(p)
            for p in (Path(__file__).resolve(), Path(__file__).resolve().parents[1] / 'autolab/memory_tie_sensitivity.py',
                      Path(__file__).resolve().parents[1] / 'autolab/analyze_memory_transfer.py')},
        registration_sha256=sha(registration_path), source_bank_sha256=sha(bank_path),
        code_archive_sha256=sha(code_zip), configuration=common, model_fingerprints=runtimes,
        groups=groups, contrasts=contrasts, visible_ticket_groups=ticket_groups,
        tie_sensitivity=describe_tie_sensitivity(rows, reg),
        curation_usage_per_bank=curation, rows=rows, artifact_sha256=fingerprints,
        limitations=['Repeated target conditions and shared memories are dependent; no population significance claim',
                     'Greedy single checkpoint executions, three deterministic tie choices, five sources per choice',
                     'Token costs are target generation only; curation charged once per bank; loading and source collection excluded',
                     'Official test identities were unused in development; public data may occur in pretraining'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'registration', 'bank', 'code-zip', 'deployment', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    result = analyze(a.root, a.registration, a.bank, a.code_zip, a.deployment)
    with a.output.open('x', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False, allow_nan=False)
        f.write('\n')
    print(json.dumps(result['groups']))


if __name__ == '__main__':
    main()
