"""Freeze all test tasks and three tied-source choices without target outcomes."""
from collections import Counter
import hashlib
import json
from pathlib import Path

from autolab.experience_memory_bank import FixedMemoryBank
from autolab.experience_tie_audit import ORDERS, SEED, TieAuditMemoryBank


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    bank_path = Path('results/remote/tau-train74-qwen3-curation-v2/memory-banks/train-qwen3-cut8-v2.json')
    tau = Path('results/third_party/tau2-bench')
    split_path = tau / 'data/tau2/domains/telecom/split_tasks.json'
    tasks_path = tau / 'data/tau2/domains/telecom/tasks.json'
    bank = json.loads(bank_path.read_bytes())
    tasks = {r['id']: r for r in json.loads(tasks_path.read_bytes())}
    splits = json.loads(split_path.read_bytes())
    ids = splits['test']
    assert len(ids) == 40 and len(set(ids)) == 40 and len(bank['records']) == 74
    assert not (set(ids) & (set(splits['small']) | set(splits['train'])))
    FixedMemoryBank(bank).assert_disjoint(ids)
    rows = []
    for uid in ids:
        ticket = tasks[uid]['ticket']
        choices = {}
        for order in ORDERS:
            chooser = TieAuditMemoryBank(bank, order)
            a, b = [chooser.retrieve(ticket, c) for c in ('full_metadata', 'boundary_aware')]
            assert a['record_id'] == b['record_id']
            if order == 'record_id':
                original = FixedMemoryBank(bank).retrieve(ticket, 'full_metadata')
                assert all(a[k] == original[k] for k in original)
            choices[order] = {k: a[k] for k in ('record_id', 'similarity', 'tied_candidates', 'tied_record_ids')}
        assert len({v['record_id'] for v in choices.values()}) == 3
        rows.append({'task_id': uid, 'ticket_sha256': hashlib.sha256(ticket.encode()).hexdigest(),
                     'choices': choices})
    report = {'purpose': __doc__, 'batch': 'tau-memory-test40-ties-v1',
              'source_bank_sha256': sha(bank_path), 'source_record_count': 74,
              'source_cutoff': bank['source_cutoff'], 'tasks_file_sha256': sha(tasks_path),
              'splits_file_sha256': sha(split_path), 'target_split': 'test',
              'selected_task_ids': ids, 'target_count': 40,
              'models': ['qwen3', 'qwen25'], 'tie_orders': list(ORDERS), 'tie_seed': SEED,
              'memory_conditions': ['full_metadata', 'boundary_aware'],
              'no_memory_baseline_once_per_model': True, 'registered_episodes': 560,
              'target_outputs_seen': False, 'rows': rows,
              'distinct_sources': {o: len({r['choices'][o]['record_id'] for r in rows}) for o in ORDERS},
              'source_use_counts': {o: dict(Counter(r['choices'][o]['record_id'] for r in rows)) for o in ORDERS},
              'source_files_sha256': {p: sha(Path(p)) for p in ('autolab/experience_memory_bank.py', 'autolab/experience_tie_audit.py')},
              'limits': 'Fixed-bank, fixed-curator sensitivity. Alternatives are two hash-ranked exact ties excluding the original choice, not an improved retrieval method, independent memory seeds or random source-population estimate.'}
    path = Path('research/evidence/memory_test40_tie_registration_v1.json')
    with path.open('x', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps({k: report[k] for k in ('source_bank_sha256', 'target_count', 'registered_episodes', 'distinct_sources', 'source_use_counts')}))


if __name__ == '__main__':
    main()
