"""Build complete answer-review packets without assigning correctness labels."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--summary', type=Path, required=True)
    p.add_argument('--evidence', type=Path, default=Path('research/evidence'))
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    cards_path = a.evidence / 'vakra_crossdomain_sql_cards_v1.json'
    policy_path = a.evidence / 'vakra_crossdomain_answer_audit_policy_v1.json'
    cards = json.loads(cards_path.read_bytes())['cards']
    policy = json.loads(policy_path.read_bytes())
    s = json.loads(a.summary.read_bytes())
    assert s['complete'] and len(s['rows']) == 240
    assert policy['sql_cards_sha256'] == sha(cards_path)
    policies = {(r['domain'], r['uuid']): r for r in policy['rows']}
    answers = {(r['domain'], r['condition'], r['model'], r['uuid']): r for r in s['rows']}
    assert len(answers) == 240 and len(policies) == len(cards) == 60
    a.output.mkdir(parents=True, exist_ok=False)
    labels = []
    for domain in s['domains']:
        packet = [f'# {domain}: complete paired answer packet',
                  'No correctness labels are assigned automatically. SQL interpretations and '
                  'reference answers are offline audit material, never agent inputs.']
        for card in (r for r in cards if r['domain'] == domain):
            pp = policies[(domain, card['uuid'])]
            packet += [f"## Task {card['task_index']:02d}: {card['uuid']}",
                       card['query'], '### Frozen interpretation',
                       '```json\n' + json.dumps({'policy': pp, 'card': card}, ensure_ascii=False, indent=2) + '\n```']
            for model in ('qwen3', 'qwen25'):
                for condition in ('original', 'coverage_check'):
                    row = answers[(domain, condition, model, card['uuid'])]
                    packet += [f'### {model} / {condition}',
                               f"Termination: {row['termination']}; source: {row['source']}",
                               '```json\n' + json.dumps(row['final_answer'], ensure_ascii=False, indent=2) + '\n```']
                    labels.append({'domain': domain, 'task_index': card['task_index'],
                                   'uuid': card['uuid'], 'model': model, 'condition': condition,
                                   'source': row['source'],
                                   'source_sha256': s['input_sha256'][row['source']],
                                   'interpretation_stratum': pp['interpretation_stratum'],
                                   'answer_label': 'pending', 'reference_compatibility': 'pending',
                                   'reason': '', 'grounding_status': 'not_scored'})
        (a.output / f'{domain}.md').write_text('\n\n'.join(packet) + '\n', encoding='utf-8')
    report = {'purpose': 'pending assistant-authored qualitative audit; not official scoring',
              'execution_summary_sha256': sha(a.summary), 'audit_cards_sha256': sha(cards_path),
              'audit_policy_sha256': sha(policy_path), 'rows': labels}
    (a.output / 'annotation_template.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'episodes': len(labels), 'domains': s['domains'], 'all_labels_pending': True}))


if __name__ == '__main__':
    main()
