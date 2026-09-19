"""Join complete capacity/expansion reviews to immutable raw episode hashes."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from autolab.vakra_review_summary import summarize_review


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'summary', 'annotations', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    summary, annotations = [json.loads(p.read_bytes()) for p in (args.summary, args.annotations)]
    evidence = Path('research/evidence')
    if summary['kind'] == 'capacity':
        cards = evidence / 'vakra_crossdomain_sql_cards_v1.json'
        policy = evidence / 'vakra_crossdomain_answer_audit_policy_v1.json'
        rules = json.loads(policy.read_bytes())['rows']
        assert json.loads(policy.read_bytes())['sql_cards_sha256'] == sha(cards)
        expected_n, expected_tasks, scored_n = 120, 60, 55
    elif summary['kind'] == 'expansion':
        cards = policy = evidence / 'vakra_domain_expansion_sql_cards_v1.json'
        rules = json.loads(cards.read_bytes())['cards']
        expected_n, expected_tasks, scored_n = 420, 70, 49
    else:
        raise ValueError('Unknown registered grid')
    for field, path in [('execution_summary_sha256', args.summary),
                        ('audit_cards_sha256', cards), ('audit_policy_sha256', policy)]:
        assert annotations[field] == sha(path), field
    root = args.root.resolve()
    for row in summary['rows']:
        path = (root / row['source']).resolve()
        assert path.is_relative_to(root)
        assert sha(path) == summary['input_sha256'][row['source']]
    result = summarize_review(summary, annotations, rules)
    assert (result['executions'], result['distinct_tasks']) == (expected_n, expected_tasks)
    assert all(r['scored_tasks'] == scored_n for r in result['groups'] if r['domain'] == 'all')
    result.update(kind=summary['kind'], execution_summary_sha256=sha(args.summary),
                  annotations_sha256=sha(args.annotations), audit_cards_sha256=sha(cards),
                  audit_policy_sha256=sha(policy),
                  analysis_source_sha256={str(p):sha(p) for p in
                    (Path(__file__), Path('autolab/vakra_review_summary.py'))})
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps(dict(executions=expected_n, distinct_tasks=expected_tasks,
                         totals=[r for r in result['groups'] if r['domain'] == 'all'])))


if __name__ == '__main__':
    main()
