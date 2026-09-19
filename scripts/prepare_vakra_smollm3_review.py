"""Render all third-model answers against the unchanged cross-domain SQL cards."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--summary', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    cards_path = Path('research/evidence/vakra_crossdomain_sql_cards_v1.json')
    policy_path = Path('research/evidence/vakra_crossdomain_answer_audit_policy_v1.json')
    cards = json.loads(cards_path.read_bytes())['cards']
    policy = json.loads(policy_path.read_bytes())
    s = json.loads(a.summary.read_bytes())
    assert s['complete'] and len(s['rows']) == 240
    assert policy['sql_cards_sha256'] == sha(cards_path)
    policies = {(r['domain'], r['uuid']): r for r in policy['rows']}
    rows = {(r['domain'], r['uuid'], r['call_policy'], r['condition']): r for r in s['rows']}
    assert len(rows) == 240 and len(cards) == len(policies) == 60
    a.output.mkdir(parents=True, exist_ok=False)
    labels = []
    for domain in s['domains']:
        packet = []
        for card in (r for r in cards if r['domain'] == domain):
            pp = policies[(domain, card['uuid'])]
            entry = {'card': card, 'policy': pp, 'answers': []}
            for execution in ('single', 'sequential'):
                for condition in ('original', 'coverage_check'):
                    row = rows[(domain, card['uuid'], execution, condition)]
                    entry['answers'].append({k: row[k] for k in ('call_policy', 'condition', 'termination', 'final_answer', 'source')})
                    labels.append({k: row[k] for k in ('domain', 'uuid', 'task_index', 'model', 'call_policy', 'condition', 'source')})
                    labels[-1].update(source_sha256=s['input_sha256'][row['source']],
                                      interpretation_stratum=pp['interpretation_stratum'],
                                      answer_label='pending', reason='', grounding_status='not_scored')
            packet.append(entry)
        (a.output / (domain + '.json')).write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding='utf-8')
    template = {'purpose': 'Assistant-authored qualitative audit, not official scoring or independent human review',
                'execution_summary_sha256': sha(a.summary), 'audit_cards_sha256': sha(cards_path),
                'audit_policy_sha256': sha(policy_path), 'rows': labels}
    (a.output / 'annotation_template.json').write_text(json.dumps(template, indent=2), encoding='utf-8')
    print(json.dumps({'episodes': len(labels), 'labels_pending': True}))


if __name__ == '__main__':
    main()
