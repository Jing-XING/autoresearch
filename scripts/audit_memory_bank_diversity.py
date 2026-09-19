"""Audit literal source-memory diversity before target results are available."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    bank_path = Path('results/remote/tau-train74-qwen3-curation-v2/memory-banks/train-qwen3-cut8-v2.json')
    registration_path = Path('research/evidence/memory_test40_tie_registration_v1.json')
    raw, reg_raw = bank_path.read_bytes(), registration_path.read_bytes()
    bank, reg = json.loads(raw), json.loads(reg_raw)
    assert sha(raw) == reg['source_bank_sha256']
    records = {r['record_id']: r for r in bank['records']}
    assert len(records) == len(bank['records']) == 74
    conditions = ('raw', 'outcome_only', 'full_metadata', 'boundary_aware')
    text_hash = {rid: {c: sha(record['memories'][c].encode()) for c in conditions}
                 for rid, record in records.items()}
    bank_diversity = {}
    for condition in conditions:
        groups = defaultdict(list)
        for rid in records:
            groups[text_hash[rid][condition]].append(rid)
        bank_diversity[condition] = dict(distinct_texts=len(groups),
            duplicate_groups=[dict(text_sha256=h, source_record_ids=ids)
                              for h, ids in sorted(groups.items()) if len(ids) > 1])
    target_groups = defaultdict(list)
    for target in reg['rows']:
        key = (target['ticket_sha256'], tuple(target['choices'][tie]['record_id'] for tie in reg['tie_orders']))
        target_groups[key].append(target['task_id'])
    selection_diversity = []
    for (ticket, ids), tasks in sorted(target_groups.items()):
        groups_by_condition = {}
        for condition in conditions:
            groups = defaultdict(list)
            for tie, rid in zip(reg['tie_orders'], ids):
                groups[text_hash[rid][condition]].append(tie)
            groups_by_condition[condition] = dict(distinct_texts=len(groups),
                identical_tie_groups=[dict(text_sha256=h, tie_orders=ties)
                                      for h, ties in groups.items() if len(ties) > 1])
        selection_diversity.append(dict(ticket_sha256=ticket, tasks=len(tasks),
            source_by_tie=dict(zip(reg['tie_orders'], ids)), diversity=groups_by_condition))
    same_full_boundary = [rid for rid in records if text_hash[rid]['full_metadata'] == text_hash[rid]['boundary_aware']]
    output = dict(purpose=__doc__, bank_sha256=sha(raw), registration_sha256=sha(reg_raw),
        script_sha256=sha(Path(__file__).read_bytes()), source_records=74,
        source_text_sha256=text_hash, bank_diversity=bank_diversity,
        selected_group_diversity=selection_diversity,
        source_ids_with_identical_full_and_boundary_text=same_full_boundary,
        protocol_decision='Keep the already registered full grid. Identify duplicate-content comparisons explicitly; do not count source IDs as distinct lessons.',
        limits='Literal equality only. Different text hashes do not establish different semantics or independent evidence. No target outcomes read.')
    path = Path('research/evidence/memory_bank_content_diversity_v1.json')
    with path.open('x', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps(dict(unique_bank_texts={c:v['distinct_texts'] for c,v in bank_diversity.items()},
        same_full_boundary=len(same_full_boundary),
        selected_groups=[dict(tasks=g['tasks'], full_distinct=g['diversity']['full_metadata']['distinct_texts'],
            duplicate_ties=g['diversity']['full_metadata']['identical_tie_groups']) for g in selection_diversity])))


if __name__ == '__main__':
    main()
