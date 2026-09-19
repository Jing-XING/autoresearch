"""Validate provenance and tabulate explicit qualitative labels, never infer them."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--evidence', type=Path, default=Path('research/evidence'))
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    summary_path = a.evidence / 'vakra_coverage12_v1_summary.json'
    cards_path = a.evidence / 'vakra_world12_semantic_audit_cards.json'
    annotations_path = a.evidence / 'vakra_coverage12_v1_answer_annotations.json'
    s = json.loads(summary_path.read_bytes())
    cards = json.loads(cards_path.read_bytes())['cards']
    labels = json.loads(annotations_path.read_bytes())
    assert labels['execution_summary_sha256'] == sha(summary_path)
    assert labels['audit_cards_sha256'] == sha(cards_path)
    expected = {(r['condition'], r['model'], r['uuid']): r for r in s['rows']}
    observed = {}
    for r in labels['rows']:
        k = (r['condition'], r['model'], r['uuid'])
        assert k in expected and k not in observed
        observed[k] = r
        original = expected[k]
        source = (a.root / r['source']).resolve()
        assert source.is_relative_to(a.root.resolve())
        assert r['source'] == original['source']
        assert r['source_sha256'] == s['input_sha256'][r['source']] == sha(source)
        assert cards[r['task_index']]['uuid'] == r['uuid']
        assert r['answer_label'] in ('correct', 'incorrect', 'no_answer', 'ambiguous')
        assert (r['answer_label'] == 'ambiguous') == (r['task_index'] == 10)
        if original['final_answer'] is None:
            assert r['answer_label'] in ('no_answer', 'ambiguous')
        if r['answer_label'] == 'correct':
            assert original['termination'] == 'agent_finished'
    assert set(observed) == set(expected) and len(observed) == 48
    groups = []
    for c in ('original', 'coverage_check'):
        for m in ('qwen3', 'qwen25'):
            rs = [r for k,r in observed.items() if k[:2] == (c,m)]
            counts = Counter(r['answer_label'] for r in rs)
            assert len(rs) == 12 and counts['ambiguous'] == 1
            groups.append({'condition': c, 'model': m, 'all_episodes': len(rs),
                           'labels': dict(counts), 'clear_interpretation_n': 11,
                           'clear_interpretation_correct': counts['correct']})
    pairs = []
    for m in ('qwen3', 'qwen25'):
        wins, losses, same = [], [], []
        for card in cards:
            x,y = (observed[(c,m,card['uuid'])] for c in ('original','coverage_check'))
            if x['answer_label'] == 'ambiguous':
                continue
            ox,cy = x['answer_label']=='correct', y['answer_label']=='correct'
            (wins if cy and not ox else losses if ox and not cy else same).append(card['uuid'])
        pairs.append({'model':m, 'wins':wins, 'losses':losses, 'unchanged':same})
    report = {'purpose':'descriptive tabulation of assistant labels, not official score or confirmation',
              'annotations_sha256':sha(annotations_path), 'groups':groups,
              'paired_clear_interpretation':pairs,
              'ambiguous_reference_matches':[
                  {k:r[k] for k in ('condition','model','uuid','reference_compatible_if_ambiguous')}
                  for r in observed.values() if r['answer_label']=='ambiguous']}
    with a.output.open('x', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps({'groups':groups,'paired':[
        {'model':r['model'],'wins':len(r['wins']),'losses':len(r['losses'])} for r in pairs]}))


if __name__ == '__main__':
    main()
