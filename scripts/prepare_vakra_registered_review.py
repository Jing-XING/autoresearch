"""Prepare complete answer-review packets without assigning correctness labels."""
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
    summary = json.loads(a.summary.read_bytes())
    partial = summary.get('closed_domain_complete', False)
    assert (summary['complete'] or partial) and summary['kind'] in ('capacity', 'expansion')
    assert not partial or (not summary['complete'] and summary['domains'] == [summary['closed_domain']])
    ev = Path('research/evidence')
    if summary['kind'] == 'expansion':
        cp = ev / 'vakra_domain_expansion_sql_cards_v1.json'
        cards = json.loads(cp.read_bytes())['cards']
        policies = {(r['domain'], r['uuid']): r for r in cards}
        policy_hash = sha(cp)
        assert len(cards) == 70
        assert sum(r['interpretation_stratum'] == 'ambiguous' for r in cards) == 21
        if partial:
            cards = [r for r in cards if r['domain'] == summary['closed_domain']]
        assert len(summary['rows']) == len(cards) * 6
    else:
        cp = ev / 'vakra_crossdomain_sql_cards_v1.json'
        pp = ev / 'vakra_crossdomain_answer_audit_policy_v1.json'
        cards = json.loads(cp.read_bytes())['cards']
        policy = json.loads(pp.read_bytes())
        assert policy['sql_cards_sha256'] == sha(cp)
        policies = {(r['domain'], r['uuid']): r for r in policy['rows']}
        policy_hash = sha(pp)
        assert len(cards) == 60 and len(summary['rows']) == 120
    expected = {(r['domain'], r['uuid'], r['model'], r['condition']): r for r in summary['rows']}
    assert len(expected) == len(summary['rows'])
    a.output.mkdir(parents=True, exist_ok=False)
    labels = []
    for domain in summary['domains']:
        packet = []
        for card in (r for r in cards if r['domain'] == domain):
            policy = policies[(domain, card['uuid'])]
            entry = {'card': card, 'policy': policy, 'answers': []}
            for model in summary['models']:
                for condition in ('original', 'coverage_check'):
                    row = expected[(domain, card['uuid'], model, condition)]
                    entry['answers'].append({k: row[k] for k in ('model', 'condition', 'termination', 'final_answer', 'source')})
                    label = {k: row[k] for k in ('domain', 'uuid', 'task_index', 'model', 'call_policy', 'condition', 'source')}
                    label.update(source_sha256=summary['input_sha256'][row['source']],
                                 interpretation_stratum=policy['interpretation_stratum'],
                                 answer_label='pending', reason='', grounding_status='not_scored')
                    labels.append(label)
            packet.append(entry)
        (a.output / (domain + '.json')).write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding='utf-8')
    assert len(labels) == len(summary['rows'])
    template = {'purpose': 'Assistant qualitative review against frozen SQL interpretations; not official scoring or independent human labels',
                'complete_batch': False, 'review_scope': summary.get('closed_domain') or 'full_registered_grid',
                'execution_summary_sha256': sha(a.summary),
                'audit_cards_sha256': sha(cp), 'audit_policy_sha256': policy_hash, 'rows': labels}
    (a.output / 'annotation_template.json').write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'episodes': len(labels), 'labels_pending': True}))


if __name__ == '__main__':
    main()
