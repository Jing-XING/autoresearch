"""Compare manuscript result tables with existing evidence, without rescoring.

Checks Tables 2--5, the executed reminder text and the preserved study record.
This is an editorial consistency check, not independent semantic adjudication.
"""
import ast
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    return json.loads((ROOT / 'research/evidence' / name).read_bytes())


def main():
    paper = ROOT / 'research/paper2'
    text = (paper / 'manuscript.md').read_text(encoding='utf-8')
    tables, current = [], []
    for line in text.splitlines() + ['']:
        if line.startswith('|'):
            cells = [s.strip() for s in line.strip('|').split('|')]
            if not all(re.fullmatch(r':?-+:?', s) for s in cells):
                current.append(cells)
        elif current:
            tables.append(current)
            current = []
    assert len(tables) == 5
    models = [('Qwen3-4B', 'qwen3'), ('Qwen2.5-7B', 'qwen25'),
              ('Qwen3-30B-A3B', 'qwen30b')]
    groups = load('vakra_expansion_complete_answer_summary_v1.json')['groups']
    def group(domain, model, condition):
        found = [g for g in groups if (g['domain'], g['model'], g['condition']) ==
                 (domain, model, condition)]
        assert len(found) == 1
        return found[0]
    expected = []
    for label, domain in [('Cookbook', 'cookbook'), ('Disney', 'disney'),
                          ('Genes', 'genes'), ('Ice hockey', 'ice_hockey_draft'),
                          ('Combined', 'all')]:
        row = [label, str(group(domain, 'qwen3', 'original')['scored_tasks'])]
        for _, model in models:
            row.append(' / '.join(str(group(domain, model, c)['correct'])
                                  for c in ('original', 'coverage_check')))
        expected.append(row)
    assert tables[1][1:] == expected, ('Table 2', tables[1][1:], expected)
    sensitivity = load('vakra_expansion_complete_sensitivity_v1.json')['primary']
    expected = []
    for label, model in models:
        r = next(r for r in sensitivity if r['model'] == model)
        low, high = r['conditional_paired_bootstrap']['interval_percentage_points']
        expected.append([label, f"{r['original_correct']}/49", f"{r['reminder_correct']}/49",
                         f"{r['gains']} / {r['losses']}",
                         f"{r['difference_percentage_points']:+.2f}", f'[{low:.2f}, {high:.2f}]'])
    assert tables[2][1:] == expected, ('Table 3', tables[2][1:], expected)
    sources = {}
    for policy, prefix in [('strict', 'vakra_crossdomain_v1'), ('sequential', 'vakra_permissive_v1')]:
        sources[policy] = (load(prefix+'_answer_summary.json')['groups'],
                           load(prefix+'_execution_summary.json')['groups'])
    expected = []
    for label, model in [('Qwen3', 'qwen3'), ('Qwen2.5', 'qwen25')]:
        for prompt, condition in [('original', 'original'), ('reminder', 'coverage_check')]:
            finals, answers = [], []
            for policy in ('strict', 'sequential'):
                answer_groups, execution_groups = sources[policy]
                a = next(g for g in answer_groups if (g['domain'], g['model'], g['condition']) ==
                         ('all', model, condition))
                n = sum(g['terminations'].get('agent_finished', 0) for g in execution_groups
                        if g['model'] == model and g['condition'] == condition and g['domain'] != 'all')
                finals.append(f'{n}/60')
                answers.append(f"{a['correct']}/55")
            expected.append([f'{label} / {prompt}', *finals, *answers])
    assert tables[3][1:] == expected, ('Table 4', tables[3][1:], expected)
    budget = load('vakra_output_budget_complete_analysis_v1.json')['rows']
    expected = []
    for label, domain in [('791 recipe names', 'cookbook'), ('129 player names', 'ice_hockey_draft')]:
        for model_label, model in models:
            pairs = [next(r for r in budget if (r['domain'], r['model'], r['condition']) ==
                          (domain, model, c)) for c in ('original', 'coverage_check')]
            expected.append([f'{label} / {model_label}',
                ' / '.join(str(int(r['primary_answer_label'] == 'correct')) for r in pairs),
                ' / '.join(str(int(r['answer_label'] == 'correct')) for r in pairs),
                ' / '.join(str(r['new_final_tokens']) for r in pairs)])
    assert tables[4][1:] == expected, ('Table 5', tables[4][1:], expected)
    tree = ast.parse((ROOT / 'autolab/vakra_native.py').read_text(encoding='utf-8'))
    conditions = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == 'INSTRUCTION_CONDITIONS' for t in n.targets))
    assert text.split('## Appendix A. Exact reminder')[1].strip() == conditions['coverage_check'].strip()
    assert hashlib.sha256((paper / 'study_record.md').read_bytes()).hexdigest() == \
        'f09f7e4d48f5c00242dcf0391e0c8768f05c773bd3d815a3415cd9c31c3de27e'
    print(json.dumps({'result_tables_checked': [2, 3, 4, 5], 'result_rows_checked': 18,
                      'exact_prompt': True, 'prior_manuscript_bytes_preserved': True,
                      'scope': 'Editorial consistency, no new scoring or experiment'}))


if __name__ == '__main__':
    main()
