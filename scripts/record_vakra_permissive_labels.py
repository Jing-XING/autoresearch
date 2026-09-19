"""Record the completed answer audit; reuse labels only for identical final text."""
from pathlib import Path
import copy
import hashlib
import json


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ev = Path('research/evidence')
    old_path = ev / 'vakra_crossdomain_v1_answer_annotations.json'
    pairing_path = ev / 'vakra_executor_pairing_v1.json'
    summary_path = ev / 'vakra_permissive_v1_execution_summary.json'
    old = json.loads(old_path.read_bytes())
    pairing = json.loads(pairing_path.read_bytes())
    summary = json.loads(summary_path.read_bytes())
    previous = {r['source']: r for r in old['rows']}
    current = {r['source']: r for r in summary['rows']}
    template = json.loads(Path('results/vakra-permissive-review-v1/annotation_template.json').read_bytes())
    # These are manually reviewed decisions, not substring-based model grading.
    reviews = {
        ('book_publishing_company', 'coverage_check', 'qwen25', 1): ('incorrect', 'Range zero is wrong for royalty 24; the stated title requires lower range 14001.'),
        ('book_publishing_company', 'coverage_check', 'qwen25', 6): ('incorrect', 'Only three employee/job pairs; omits Maria Pontes and Philip Cramer.'),
        ('book_publishing_company', 'coverage_check', 'qwen25', 7): ('incorrect', 'Omits three titles and misassigns sales for Net Etiquette, Emotional Security and Fifty Years.'),
        ('book_publishing_company', 'coverage_check', 'qwen25', 15): ('correct', 'Requested distinct-publisher count is three. Auxiliary filtering claims are not validated by this answer label.'),
        ('book_publishing_company', 'coverage_check', 'qwen25', 16): ('incorrect', 'Gives an incorrect title/amount instead of the requested mod_cook type.'),
        ('book_publishing_company', 'original', 'qwen25', 3): ('incorrect', 'Gives Aria Cruz rather than Yoshi Latimer, hired 1989-06-11.'),
        ('book_publishing_company', 'original', 'qwen25', 6): ('incorrect', 'All three named employees differ from the required five employee/job pairs.'),
        ('book_publishing_company', 'original', 'qwen25', 10): ('incorrect', 'Names Aria, Martin and Peter instead of Annette, Diego, Matti and Victoria.'),
        ('book_publishing_company', 'original', 'qwen25', 15): ('correct', 'Correctly gives three distinct USA publishers with qualifying titles.'),
        ('book_publishing_company', 'original', 'qwen25', 16): ('incorrect', 'Answers business after grouping advances; frozen maximum-single-title interpretation gives mod_cook. Alternative aggregation wording remains a limitation.'),
        ('book_publishing_company', 'original', 'qwen25', 19): ('incorrect', 'VPA30890F is not the frozen job-level answer F-C16315M and has a middle initial. Previously observed highest-ID/job-level ambiguity is retained.'),
        ('cars', 'coverage_check', 'qwen25', 1): ('correct', 'Correctly gives 78. Tool-call difficulties do not alone invalidate the numerical final answer.'),
        ('cars', 'coverage_check', 'qwen25', 4): ('correct', 'Correctly gives USA. Its explicit assumption about the country code is not proof of tool grounding.'),
        ('cars', 'coverage_check', 'qwen25', 5): ('incorrect', 'Gives 453 instead of the required 45 rows.'),
        ('cars', 'coverage_check', 'qwen25', 6): ('incorrect', 'Truncated list is not all 187 USA names and includes non-USA entries.'),
        ('cars', 'coverage_check', 'qwen25', 7): ('incorrect', 'Omits highest-priced Plymouth Fury Gran Sedan and includes fourth-ranked VW Rabbit C.'),
        ('cars', 'coverage_check', 'qwen25', 9): ('incorrect', 'Truncated unrestricted weights differ from the required 42 price-filtered weights.'),
        ('cars', 'coverage_check', 'qwen25', 12): ('ambiguous', 'Preidentified row-count versus distinct-model ambiguity; no final answer after protocol error limit.'),
        ('cars', 'original', 'qwen25', 5): ('incorrect', 'Gives 56 instead of 45 under the frozen row-count interpretation.'),
        ('cars', 'original', 'qwen25', 6): ('incorrect', 'Eleven names followed by an ellipsis do not exhaust the 187 distinct USA names.'),
        ('cars', 'original', 'qwen25', 9): ('incorrect', 'Only three of the required 42 weights are provided.'),
        ('cars', 'original', 'qwen25', 10): ('incorrect', 'Gives unrestricted maximum 24.8 instead of price-filtered maximum 21.7.'),
        ('cars', 'original', 'qwen25', 13): ('incorrect', 'Incorrectly claims Chevrolet Malibu is absent; its country is USA.'),
        ('cars', 'original', 'qwen25', 15): ('correct', 'Correctly gives USA.'),
        ('cars', 'original', 'qwen3', 2): ('incorrect', 'Output ends in a price list without giving the requested acceleration 14.5.'),
        ('computer_student', 'coverage_check', 'qwen25', 10): ('incorrect', 'Gives 40 rather than three under frozen Faculty_eme glossary interpretation.'),
        ('computer_student', 'original', 'qwen25', 14): ('ambiguous', 'Preidentified course/faculty-scope ambiguity; zero matches neither six distinct courses nor reference 27 assignments.'),
    }
    equal = {r['source']: r['final_text_equal'] for r in pairing['rows']}
    used = set()
    for r in template['rows']:
        source = r['source']
        r['grounding_status'] = 'not_scored'
        if equal[source]:
            for key in ('answer_label', 'reference_compatibility', 'reason'):
                r[key] = copy.deepcopy(previous[source][key])
            r['annotation_basis'] = 'inherited: byte-identical final text, same question/database, verified pairing'
        else:
            key = (r['domain'], r['condition'], r['model'], r['task_index'])
            label, reason = reviews[key]
            used.add(key)
            r.update(answer_label=label, reason=reason, annotation_basis='assistant review of changed final answer against frozen card')
            r['reference_compatibility'] = ('no_answer' if current[source]['final_answer'] is None
                                            else 'compatible' if label == 'correct' else 'incompatible')
    assert used == set(reviews) and len(used) == 27
    template.update(purpose='complete descriptive assistant-authored answer audit; not official score or independent human annotation',
                    complete_batch=True, prior_annotations_sha256=sha(old_path), pairing_sha256=sha(pairing_path),
                    inherited_identical_final_answers=213, manually_reviewed_changed_final_answers=27,
                    post_outcome_limitations=['Frozen interpretations retained despite books16 aggregation and books19 highest-employee ambiguity; these are not silently removed.',
                                             'Identical answers support label reuse only, not inheritance of grounding or explanation-trajectory consistency.'])
    assert template['execution_summary_sha256'] == sha(summary_path)
    out = ev / 'vakra_permissive_v1_answer_annotations.json'
    with out.open('x', encoding='utf-8') as f:
        json.dump(template, f, ensure_ascii=False, indent=2)
    print('Recorded 240 labels: 213 identical-text reuse, 27 changed-answer reviews')


if __name__ == '__main__':
    main()
