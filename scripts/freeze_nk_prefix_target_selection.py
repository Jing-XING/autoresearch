"""Freeze source choice using visible test tickets, never target outcomes."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from autolab.experience_memory_bank import FixedMemoryBank


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path,
                        default=Path('research/evidence/nk_prefix_target_selection_v1.json'))
    args = parser.parse_args()
    preparation_path = Path('results/preparations/nk-prefix-v1-final/manifest.json')
    preparation = json.loads(preparation_path.read_bytes())
    bank_path = Path('results/remote/tau-train74-qwen3-curation-v2/memory-banks/train-qwen3-cut8-v2.json')
    bank = json.loads(bank_path.read_bytes())
    registration_path = Path('research/evidence/memory_test40_tie_registration_v1.json')
    old = json.loads(registration_path.read_bytes())
    tasks_path = Path('results/third_party/tau2-bench/data/tau2/domains/telecom/tasks.json')
    assert sha(tasks_path) == old['tasks_file_sha256'] and sha(bank_path) == old['source_bank_sha256']
    tasks = {t['id']: t for t in json.loads(tasks_path.read_bytes())}
    allowed = set(preparation['selected_record_ids'])
    bank['records'] = [r for r in bank['records'] if r['record_id'] in allowed]
    assert len(bank['records']) == 70
    retriever = FixedMemoryBank(bank)
    retriever.assert_disjoint(old['selected_task_ids'])
    old_by = {r['task_id']: r for r in old['rows']}
    rows = []
    for uid in old['selected_task_ids']:
        ticket = tasks[uid]['ticket']
        selected = retriever.retrieve(ticket, 'raw')
        ticket_hash = hashlib.sha256(ticket.encode()).hexdigest()
        assert ticket_hash == old_by[uid]['ticket_sha256']
        rows.append({'task_id': uid, 'ticket_sha256': ticket_hash,
                     'source_choice': {k: selected[k] for k in ('record_id', 'similarity', 'tied_candidates', 'pool_size')},
                     'original_74_source_choice': old_by[uid]['choices']['record_id']['record_id']})
    report = {'schema': 'autolab.nk_prefix_target_selection.v1',
        'status': 'source_choices_frozen_before_curation; target execution not yet registered',
        'preparation_manifest_sha256': sha(preparation_path), 'original_source_bank_sha256': sha(bank_path),
        'source_pool_size': 70, 'selected_source_ids': sorted(allowed),
        'original_test_registration_sha256': sha(registration_path), 'tasks_file_sha256': sha(tasks_path),
        'target_count': len(rows), 'target_outputs_seen': False, 'curation_outputs_seen': False,
        'retrieval': 'visible ticket TF-IDF cosine; top-1; record-id tie break; shared eligible pool',
        'rows': rows, 'source_use_counts': dict(Counter(r['source_choice']['record_id'] for r in rows)),
        'changed_source_choices': sum(r['source_choice']['record_id'] != r['original_74_source_choice'] for r in rows),
        'invalid_curation_policy': 'retain source choice and inject empty experience under common wrapper; no replacement'}
    with args.output.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps({'target_count': len(rows), 'changed_source_choices': report['changed_source_choices'],
                      'output_sha256': sha(args.output)}))


if __name__ == '__main__':
    main()
