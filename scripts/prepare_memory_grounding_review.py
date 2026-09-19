"""Prepare complete recorded message prefixes for registered test-selected memories.

This reads the frozen source bank and retrieval registration only, never source
continuation labels or target model results. Annotation is descriptive and manual.
"""
import hashlib
import json
from pathlib import Path


def main():
    bank_path = Path('results/remote/tau-train74-qwen3-curation-v2/memory-banks/train-qwen3-cut8-v2.json')
    registration_path = Path('research/evidence/memory_test40_tie_registration_v1.json')
    bank_raw, reg_raw = bank_path.read_bytes(), registration_path.read_bytes()
    bank, registration = json.loads(bank_raw), json.loads(reg_raw)
    sha = lambda value: hashlib.sha256(value).hexdigest()
    assert sha(bank_raw) == registration['source_bank_sha256']
    selected = sorted({choice['record_id'] for row in registration['rows']
                       for choice in row['choices'].values()})
    records = {record['record_id']: record for record in bank['records']}
    assert len(selected) == 15 and len(records) == 74
    packets = []
    for record_id in selected:
        memories = records[record_id]['memories']
        visible = json.loads(memories['raw'])
        assert set(visible) == {'generation_budget', 'observed_benchmark_reward',
            'observed_history', 'source_ticket', 'stop_reason'}
        packets.append(dict(record_id=record_id,
            source_prefix=visible, raw_memory_sha256=sha(memories['raw'].encode()),
            lessons={condition: dict(text=memories[condition],
                       sha256=sha(memories[condition].encode()))
                     for condition in ('outcome_only', 'full_metadata', 'boundary_aware')}))
    result = dict(purpose=__doc__, bank_sha256=sha(bank_raw),
        registration_sha256=sha(reg_raw), script_sha256=sha(Path(__file__).read_bytes()),
        review_scope='All 15 selected source IDs, 45 lessons; sources selected without target outcomes. Not a random sample of the bank. Raw memory omits the source policy; this packet is not the entire curator input. Assess recorded factual claims, not policy compliance of recommendations.',
        rubric={
            'supported': 'The cited visible observation supports the specific factual claim at its stated time and entity.',
            'contradicted': 'A visible observation contradicts the stated factual claim.',
            'unsupported': 'Available prefix does not establish the asserted cause, post-action state, result, or exclusion.',
            'recommendation': 'Normative or conditional advice is not automatically a claim that the intervention already succeeded.',
            'limits': 'Claim-level examples, not exhaustive factuality rates; no hidden-state or future-label adjudication; no causal attribution to target failures.'},
        records=packets)
    target = Path('results/reviews/memory-test40-source-grounding-v1.json')
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps(dict(records=len(packets), lessons=sum(len(p['lessons']) for p in packets),
        packet_sha256=sha(target.read_bytes()), path=str(target))))


if __name__ == '__main__':
    main()
