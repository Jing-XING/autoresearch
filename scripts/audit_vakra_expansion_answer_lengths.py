"""Measure explicit reference-answer serialization lengths before model outcomes.

Reference length is a resource-risk diagnostic, not a lower bound on every
semantically equivalent answer and not a reason to exclude registered tasks.
"""
import hashlib
import importlib.metadata
import json
from pathlib import Path
from tokenizers import Tokenizer


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    path = Path('research/evidence/vakra_domain_expansion_sql_cards_v1.json')
    cards = json.loads(path.read_bytes())['cards']
    tokenizer_path = Path('results/models/qwen30b/tokenizer.json')
    assert sha(tokenizer_path) == 'aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4'
    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    rows = []
    for card in cards:
        values = card['answer_rows']
        # Remove only the explicitly auxiliary columns noted in the SQL cards.
        if (card['domain'], card['task_index']) in {('cookbook', 5), ('cookbook', 15), ('genes', 7)}:
            values = [[r[1]] for r in values]
        elif (card['domain'], card['task_index']) == ('ice_hockey_draft', 2):
            values = [[r[1]] for r in values]
        # A unique-value list is an alternative surface for list queries, not
        # an automatic replacement for cardinality-sensitive grading.
        unique = list(dict.fromkeys(json.dumps(r, ensure_ascii=False, separators=(',', ':')) for r in values))
        renderings = {
            'compact_rows_json': json.dumps(values, ensure_ascii=False, separators=(',', ':')),
            'line_separated_rows': '\n'.join('\t'.join(str(v) for v in r) for r in values),
            'unique_rows_json': '[' + ','.join(unique) + ']',
        }
        lengths = {name: len(tokenizer.encode(text, add_special_tokens=False).ids) for name,text in renderings.items()}
        rows.append({'domain':card['domain'], 'task_index':card['task_index'], 'uuid':card['uuid'],
                     'answer_rows':len(values), 'distinct_rows':len(unique), 'token_counts':lengths,
                     'all_three_renderings_over_512': min(lengths.values()) > 512})
    report = {'purpose':__doc__, 'cards_sha256':sha(path), 'tokenizer_sha256':sha(tokenizer_path),
              'tokenizer_model':'Qwen3-30B-A3B-Instruct-2507',
              'tokenizers_version':importlib.metadata.version('tokenizers'), 'model_outputs_seen':False,
              'rows':rows, 'flagged_tasks':[r for r in rows if r['all_three_renderings_over_512']],
              'limits':'Does not prove a shortest-answer lower bound, measure tool-result input lengths, or evaluate generated answers. Auxiliary columns removed only as documented. No new exclusions, prompt changes or budget changes. Use this diagnostic when interpreting fixed-budget performance and later explicitly registered budget sensitivity.'}
    with Path('research/evidence/vakra_expansion_answer_lengths_v1.json').open('x',encoding='utf-8') as f:
        json.dump(report,f,ensure_ascii=False,indent=2)
    print(json.dumps(report['flagged_tasks'],ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
