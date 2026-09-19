"""Literal assistant review notes; no correctness inference from substrings."""
import hashlib
import json
from pathlib import Path

ARMS = [('single', 'original'), ('single', 'coverage_check'),
        ('sequential', 'original'), ('sequential', 'coverage_check')]
LABELS = {'I': 'incorrect', 'C': 'correct', 'A': 'ambiguous'}
# Every string follows ARMS order. These entries are added only after full
# task-local answer review; missing entries prevent a complete audit export.
REVIEWS = {
    'computer_student': [
        ('IIII', 'Required count is 6. Original-single gives a proposed procedure; reminder answers 2; sequential-original has no final answer.'),
        ('IIII', 'Required 82 course IDs are not supplied: omitted/placeholder list, proposed calls, retry instructions, or false empty-set claim.'),
        ('IIII', 'Required count is 8. Three arms provide procedures without a numeric result; sequential reminder answers 82.'),
        ('AAAA', 'Preidentified professor-scope ambiguity retained. Single original gives only 40 and 180; other arms give retry/procedure text, not a full ID set.'),
        ('IIII', 'Required seven course IDs are absent. Single original gives course1_id/course2_id placeholders; two arms give repair/procedure text; sequential reminder has no answer.'),
        ('IIII', 'None gives the thirteen advisor IDs. Single original supplies an unrelated one-row preview; others propose filtering, decline, or repeat repair advice.'),
        ('IIIC', 'Only sequential reminder reports Level_400. Original arms repeat an unavailable-key error; single reminder provides unevaluated calls.'),
        ('IIII', 'Original arms answer 96,118,183 instead of 101,179,234. Reminder arms provide incomplete procedures.'),
        ('IIII', 'Required count is 8. Sequential original guesses 132; remaining arms provide unevaluated procedures.'),
        ('IIII', 'Required count is 5. Sequential original answers 2; other arms have no final answer or only retry/procedure text.'),
        ('IIII', 'Required count is 3. No arm supplies it; three give procedure/retry text and sequential reminder exhausts tool budget.'),
        ('AAAA', 'Preidentified course-versus-assignment ambiguity retained. All four responses propose unevaluated counting procedures.'),
        ('IIII', 'Required employee ID is 375. Sequential reminder lists 40,40,180 from a preview; remaining arms supply procedures or repair text.'),
        ('IIII', 'Required membership answer is yes/Faculty. Sequential original says no; single original has no answer; reminder arms provide incomplete procedures.'),
        ('AAAA', 'Preidentified course/assignment/faculty scope ambiguity retained. Sequential reminder says 2, two arms propose procedures, single original has no answer.'),
        ('IIII', 'Required eight course IDs absent. Original arms list 21,38,49 or 99,204,263; reminder arms repeat repair instructions.'),
        ('IIII', 'Required advisor count is 13. Reminders answer 5 or 3; original arms only propose counting procedures.'),
        ('IIII', 'Required six people IDs absent. Original arms answer person 18; reminders propose calls or retry instructions.'),
        ('IIII', 'Sequential reminder gives correct Level_300 but only 52,57,165 of seven people. Other arms have no answer or wrong level/IDs.'),
        ('IIII', 'Required pair 297/Faculty_eme absent. Single arms and sequential original give procedures; sequential reminder reports unrelated preview 40,40,180/Faculty.')
    ],
    'cars': [
        ('IIII', 'Required Plymouth Fury Gran Sedan name absent. All arms provide procedures or retry text.'),
        ('IIII', 'Required count is 78. Sequential original gives 109; others provide procedures or no answer.'),
        ('IIII', 'Required acceleration 14.5 absent; three arms provide procedures and sequential original has no answer.'),
        ('IIII', 'Required Ford Torino price 20000 absent. All arms defer to proposed future tool calls.'),
        ('ICIC', 'Both reminders name United States as the likely origin, consistent with SQL, while deferring verification. Credit is for the named answer only; explicitly qualified and sensitivity-flagged. Original arms give a country placeholder.'),
        ('IIII', 'Required count 45 absent. Three arms give procedures and single reminder has no answer.'),
        ('IIII', 'Required full car-name list absent; all four arms only propose filtering/retrieval.'),
        ('IIII', 'Required three car names absent; all four arms only propose procedures.'),
        ('IIII', 'Original arms give retry instructions. Reminders list 1970 through 1982 rather than only 1970,1971,1972,1973.'),
        ('IIII', 'Single arms give procedure text. Sequential arms return a superset including 2672,4376 and other weights outside the requested subset.'),
        ('IIII', 'Required maximum acceleration 21.7 absent; all four arms only propose procedures.'),
        ('IIII', 'Required average price is about 28982.18. Sequential original answers 25.5; other arms only propose procedures.'),
        ('AAAA', 'Preidentified distinct-car versus production-record ambiguity retained. Sequential reminder invents a hypothetical count 300; other arms give procedures.'),
        ('IIII', 'Required USA absent. Original arms have no answer; reminder arms defer to future retrieval.'),
        ('IIII', 'Required MPG 14 absent; all four arms give procedures or truncated code.'),
        ('IIIC', 'Only sequential reminder supplies USA. Other arms give procedures or claim an unspecified result is available.'),
        ('IIII', 'Required price 20000 absent; outputs decline, claim absent data, or provide repair/procedure text.'),
        ('IICC', 'Both sequential arms report engine displacement 200.0. Single arms only propose procedures.'),
        ('IIII', 'Required year 1980/80 absent. All arms defer to proposed retrieval.'),
        ('AAAA', 'Preidentified fastest-car proxy ambiguity retained; all arms give procedures without an origin-country answer.')
    ],
    'book_publishing_company': [
        ('IIII', 'Required top title Onions, Leeks, and Garlic absent. Original arms invent title_1/50; reminders give unfinished procedures.'),
        ('IIII', 'No arm supplies a maximum-royalty title with its correct lower range; outputs defer, speculate 100 percent, or have no answer.'),
        ('IIII', 'Three arms list only the first three of eleven employees; sequential reminder has no final answer.'),
        ('IIII', 'Required Yoshi Latimer and 1989-06-11 absent; outputs give procedures or hypothetical Aria Cruz data.'),
        ('IIII', 'Required CEO Philip Cramer and 1989-11-11 absent. Single reminder invents Aria/empty date; others give procedures or repair text.'),
        ('IIII', 'Single reminder incorrectly gives The Busy Executive\'s Database Guide/19.99; other arms have no final answer.'),
        ('IIII', 'Required five complete employee-name/job-description pairs absent; all arms give procedures or repair text.'),
        ('IIII', 'Required seventeen distinct title/sales pairs absent; one arm has no final answer and others give incomplete code or calls.'),
        ('IIII', 'Required You Can Combat Computer Stress! title absent; all arms give procedures or truncated code.'),
        ('IIII', 'Required publisher count is 6. Three arms answer 3; single reminder only proposes calls.'),
        ('IIII', 'Required Annette, Diego, Matti and Victoria absent; all arms defer to future retrieval.'),
        ('IIII', 'Required level 100 absent; all arms only describe procedures.'),
        ('IIII', 'Required best-selling book price 10.95 absent; all arms only describe procedures or repeat text.'),
        ('IIII', 'Required USA absent; all arms only propose retrieval.'),
        ('IIII', 'Required publisher Algodata Infosystems absent; all arms give code/procedures.'),
        ('IIII', 'Required count 3 absent; all arms give incomplete or repetitive procedures.'),
        ('IIII', 'Required mod_cook absent; all arms propose procedures. Later-noted group-sum wording uncertainty does not change the fixed subtotal.'),
        ('IIII', 'Required royalty 24 absent. Single original invents 50000; other arms give procedures or repair text.'),
        ('IIII', 'Required job level 100 absent; all arms give procedures or decline without an exact level.'),
        ('IIII', 'No requested employee ID supplied: one arm has no answer and others give procedures. Later-noted highest-ID versus highest-job-level wording uncertainty is retained without changing the fixed subtotal.')
    ],
}


def main():
    folder = Path('results/vakra-smollm3-review-v1')
    template_path = folder / 'annotation_template.json'
    report = json.loads(template_path.read_bytes())
    assert len(REVIEWS) == 3 and all(len(v) == 20 for v in REVIEWS.values()), 'All 60 task reviews required'
    for row in report['rows']:
        labels, reason = REVIEWS[row['domain']][row['task_index']]
        assert len(labels) == 4
        label = LABELS[labels[ARMS.index((row['call_policy'], row['condition']))]]
        assert (label == 'ambiguous') == (row['interpretation_stratum'] == 'ambiguous')
        row.update(answer_label=label, reason=reason,
                   annotation_basis='Full final-answer reading; identical texts deduplicated only within the same task')
        row['qualified_answer_sensitivity'] = row['domain'] == 'cars' and row['task_index'] == 4 and row['condition'] == 'coverage_check'
    report.update(complete_batch=True, reviewed_episodes=240,
                  annotation_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  post_outcome_limitations='Frozen SQL subtotal and preflagged ambiguity strata unchanged. Publishing task 19 later-detected wording ambiguity remains in subtotal. No trajectory grounding score inferred from answer labels.')
    out = Path('research/evidence/vakra_smollm3_v1_answer_annotations.json')
    with out.open('x', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(json.dumps({'episodes': len(report['rows']), 'complete': True}))


if __name__ == '__main__':
    main()
