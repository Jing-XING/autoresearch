"""Audit a complete paired memory grid and report descriptive treatment contrasts.

No significance claim: target families and reused source memories are dependent.
Run errors remain in the registered denominator and count as non-successes.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from autolab.summarize_tau2_native import summarize

CONDITIONS = ('none', 'raw', 'outcome_only', 'full_metadata', 'boundary_aware')


def paired_contrast(treatment, control):
    def index(rows):
        values = {}
        for row in rows:
            key = (row['model'], row['task_id'])
            if key in values or row.get('pending'):
                raise ValueError('Duplicate or pending paired observation')
            values[key] = row
        return values
    a, b = index(treatment), index(control)
    if not a or a.keys() != b.keys():
        raise ValueError('Paired task coverage differs')
    groups = []
    for model in sorted({key[0] for key in a}):
        keys = sorted(key for key in a if key[0] == model)
        wins = [task for m, task in keys if a[(m, task)]['reward'] == 1 and b[(m, task)]['reward'] != 1]
        losses = [task for m, task in keys if a[(m, task)]['reward'] != 1 and b[(m, task)]['reward'] == 1]
        groups.append({'model': model, 'tasks': len(keys), 'wins': wins, 'losses': losses,
                       'success_difference': (len(wins) - len(losses)) / len(keys),
                       'interpretation': 'descriptive paired difference, not an independent-sample significance test'})
    return groups


def analyze(root, bank_path):
    bank_bytes = bank_path.read_bytes()
    bank_hash = hashlib.sha256(bank_bytes).hexdigest()
    bank = json.loads(bank_bytes)
    arms, reference, weights, task_hashes, selections = {}, None, {}, {}, {}
    for condition in CONDITIONS:
        directory = root / condition
        summary = summarize(directory)
        if not summary['complete']:
            raise ValueError(f'Incomplete grid condition: {condition}')
        config = dict(summary['configuration'])
        expected = None if condition == 'none' else condition
        if config.pop('memory_condition') != expected:
            raise ValueError('Condition label disagrees with recorded configuration')
        if config.pop('memory_bank_sha256') != (None if condition == 'none' else bank_hash):
            raise ValueError('Recorded memory bank differs from the supplied bank')
        if reference is not None and config != reference:
            raise ValueError('Task/decoder/adapter configuration changes across treatments')
        reference = config
        if set(config['all_task_ids']) & set(bank['source_task_ids']):
            raise ValueError('Source/target overlap')
        for path in sorted(directory.glob('*/shard-*/manifest.json')):
            manifest = json.loads(path.read_bytes())
            model = path.parent.parent.name
            current = {'weights': manifest['model_files_sha256'], 'packages': manifest['packages']}
            if model in weights and weights[model] != current:
                raise ValueError('Model weights or runtime packages differ across treatments')
            weights[model] = current
            if set(manifest['task_sha256']) != set(manifest['selected_task_ids']):
                raise ValueError('Task fingerprints do not cover selected tasks')
            for task_id, value in manifest['task_sha256'].items():
                if task_id in task_hashes and task_hashes[task_id] != value:
                    raise ValueError('Task content differs across treatments')
                task_hashes[task_id] = value
            if condition != 'none':
                for audit_file in sorted(path.parent.glob('case-*-model-audit.json')):
                    audit = json.loads(audit_file.read_bytes())
                    if not audit['calls']:
                        continue  # Run error remains counted in summarize().
                    selected = dict(audit['calls'][0]['memory_selection'])
                    if selected.pop('condition') != condition:
                        raise ValueError('Agent audit condition mismatch')
                    task_id = audit['task_id']
                    if task_id in selections and selections[task_id] != selected:
                        raise ValueError('Retrieved source differs by treatment or target model')
                    selections[task_id] = selected
        arms[condition] = summary
    usage = []
    for condition, summary in arms.items():
        for model in sorted(weights):
            rows = [r for r in summary['rows'] if r['model'] == model]
            total = Counter()
            for row in rows:
                total.update(row['usage'])
            usage.append({'condition': condition, 'model': model, 'tasks': len(rows),
                          'successes': sum(r['reward'] == 1 for r in rows),
                          'run_errors': sum(r['reward'] is None for r in rows),
                          'target_generation_usage': dict(total)})
    curation = {}
    for condition in CONDITIONS[2:]:
        total = Counter()
        for record in bank['records']:
            total.update(record['curation_usage'][condition])
        curation[condition] = dict(total)
    contrasts = {'primary_development_boundary_vs_full': paired_contrast(
        arms['boundary_aware']['rows'], arms['full_metadata']['rows'])}
    for condition in CONDITIONS[1:]:
        contrasts[condition + '_vs_none'] = paired_contrast(arms[condition]['rows'], arms['none']['rows'])
    return {'purpose': 'complete public-development comparison; no confirmatory claim',
            'complete': True, 'memory_bank_sha256': bank_hash, 'configuration': reference,
            'model_runtime_fingerprints': weights, 'target_summary': usage,
            'source_bank_curation_usage': curation,
            'cost_boundary': 'Generation metrics exclude loading/hosting overhead and source collection; curation is counted once per bank, not once per target model.',
            'paired_contrasts': contrasts, 'retrieval': selections,
            'unique_selected_sources': len({s['record_id'] for s in selections.values()}),
            'arms': arms}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--bank', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    value = analyze(args.root, args.bank)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
    print(json.dumps(value['target_summary']))


if __name__ == '__main__':
    main()
