"""Validate annotation provenance and verbatim evidence references, not semantic labels."""
import hashlib
import json
from pathlib import Path


def main():
    base = Path('research/evidence')
    path = base / 'memory_test40_selected_grounding_review_v1.json'
    review = json.loads(path.read_bytes())
    bank_path = Path('results/remote/tau-train74-qwen3-curation-v2/memory-banks/train-qwen3-cut8-v2.json')
    raw = bank_path.read_bytes()
    sha = lambda data: hashlib.sha256(data).hexdigest()
    assert sha(raw) == review['bank_sha256']
    records = {r['record_id']: r for r in json.loads(raw)['records']}
    reg_path = base / 'memory_test40_tie_registration_v1.json'
    reg = json.loads(reg_path.read_bytes())
    selected = {c['record_id'] for r in reg['rows'] for c in r['choices'].values()}
    assert len(review['records']) == len(selected) == review['reviewed_source_ids']
    assert {r['record_id'] for r in review['records']} == selected
    count = 0
    for annotation in review['records']:
        source = records[annotation['record_id']]
        messages = json.loads(source['memories']['raw'])['observed_history']
        observed_tools = {m['tool_call_id'] for m in messages if m['role'] == 'tool'}
        duplicate = annotation.get('duplicate_visible_content_of')
        if duplicate:
            assert source['memories'] == records[duplicate]['memories']
        for claim in annotation['claims']:
            assert claim['quote'] in source['memories'][claim['condition']], claim
            assert set(claim['tool_call_ids']) <= observed_tools, claim
            count += 1
    report = dict(annotation_sha256=sha(path.read_bytes()), bank_sha256=sha(raw),
        registration_sha256=sha(reg_path.read_bytes()), script_sha256=sha(Path(__file__).read_bytes()),
        records=len(selected), claim_examples=count, exact_quotes_verified=True,
        referenced_tool_responses_exist=True, duplicate_content_verified=True,
        semantic_labels_automatically_verified=False,
        note='These checks verify provenance, not independent correctness of the one-reviewer interpretations.')
    output = base / 'memory_test40_selected_grounding_validation_v1.json'
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
