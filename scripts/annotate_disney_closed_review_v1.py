"""Materialize the complete, unblinded assistant review of frozen Disney cards.

The labels below were assigned after reading all 120 full final responses.
This script records that review; it is not an automatic semantic scorer.
"""
import json
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    review = json.loads((root / 'results/reviews/vakra-expansion-disney-v1/disney.json').read_bytes())
    annotations = json.loads((root / 'results/reviews/vakra-expansion-disney-v1/annotation_template.json').read_bytes())
    # Qwen3 original/reminder, Qwen2.5 original/reminder, Qwen30B original/reminder.
    labels = [
        'CCCCCC', 'AAAAAA', 'CCCICC', 'CCNCNC', 'CIIIIC',
        'CCIICC', 'ICICCC', 'CIIIII', 'IIIIIC', 'CCIICC',
        'CCCCCC', 'CIICCC', 'CIIICC', 'IIIICC', 'AAAAAA',
        'CCCCII', 'IIIICC', 'IICICC', 'CCICCC', 'IIIIII',
    ]
    gold_reasons = {
        0: 'Gives the requested count 7.',
        2: 'Gives the requested Horror count 6.',
        3: 'Gives the requested MPAA rating PG.',
        4: 'Identifies Maggie, matching the fixed hero field.',
        5: 'Identifies Ben Sharpsteen without adding another director as the answer.',
        6: 'Gives the requested total gross $97,822,171.',
        7: 'Lists both distinct requested titles: 101 Dalmatians and The Aristocats. Repeated 101 Dalmatians with release years does not introduce a third distinct title under the frozen title-only SQL.',
        8: 'Identifies Hiro Hamada.',
        9: 'The response explicitly provides both When You Wish upon a Star and Baby Mine, with the corresponding films. Both requested values are present in the final response.',
        10: 'Gives the requested genre Adventure.',
        11: 'Final corrected answer provides Mulan, Barry Cook and 19-Jun-98 / June 19, 1998.',
        12: 'Gives the requested count 2.',
        13: 'Identifies Stephen J. Anderson.',
        15: 'Gives 24-Jun-94 / June 24, 1994.',
        16: 'Identifies The Many Adventures of Winnie the Pooh.',
        17: 'Gives the requested genre Adventure.',
        18: 'Lists all five non-null reference villains, with no extra villain; a note about one null is not an additional villain.',
    }
    wrong_reasons = {
        2: 'Reports 13 and concedes this is an unfiltered count; the fixed Horror count is 6.',
        4: 'Does not identify Maggie; instead denies a matching movie or identifies Kuzco.',
        5: 'Adds David Hand as a Pinocchio director; the frozen database answer is Ben Sharpsteen only.',
        6: 'Gives a different gross amount and movie; the requested amount is $97,822,171.',
        7: 'Does not give exactly the two requested titles under the frozen G-rating interpretation: denies them, substitutes other titles, or adds titles with other/missing ratings.',
        8: 'Does not identify Hiro Hamada; gives Elsa/Hercules or denies a matching record.',
        9: 'Does not provide both requested song names: denies a matching record or provides only When You Wish upon a Star.',
        11: 'Fails the requested three-field answer: director is missing or incorrectly given as Mulan, or release date is missing.',
        12: 'Reports zero or cannot determine; the fixed count is 2.',
        13: 'Does not identify Stephen J. Anderson; denies a matching record or substitutes a different director.',
        15: 'Gives June 21, 1996 rather than June 24, 1994.',
        16: 'Denies a movie without a villain; the frozen answer is The Many Adventures of Winnie the Pooh.',
        17: 'Cannot determine a genre rather than providing Adventure.',
        18: 'Denies matching movies and provides none of the five requested villains.',
        19: 'Names Winnie the Pooh, Snow White, The Little Mermaid or Lilo & Stitch rather than Bolt.',
    }
    positions = [(m,c) for m in ('qwen3','qwen25','qwen30b') for c in ('original','coverage_check')]
    by_identity = {(t['card']['task_index'],a['model'],a['condition']): a for t in review for a in t['answers']}
    expanded = {'C':'correct','I':'incorrect','N':'no_answer','A':'ambiguous'}
    for row in annotations['rows']:
        idx = row['task_index']; arm = (row['model'],row['condition'])
        label = labels[idx][positions.index(arm)]
        raw = by_identity[idx,*arm]
        assert raw['source'] == row['source']
        row['answer_label'] = expanded[label]
        if label == 'A':
            row['reason'] = ('Frozen pre-run ambiguity: popularity metric is unspecified' +
                (' and the global maximum/join scope also changes the answer' if idx == 14 else '') +
                '. Excluded from answer accuracy regardless of response; execution and costs retained. Termination: ' + raw['termination'] + '.')
        elif label == 'N':
            assert raw['final_answer'] is None
            row['reason'] = 'No final answer: ' + raw['termination'] + '. Retained as unsuccessful in the fixed denominator.'
        else:
            assert raw['final_answer'] is not None
            row['reason'] = (gold_reasons if label == 'C' else wrong_reasons)[idx]
        if idx == 3 and arm == ('qwen3','original'):
            row['reason'] += ' The truncated response attributes Turbo to the wrong film, The Incredibles, and explicitly guesses. The requested rating matches; this label does not certify its explanation or grounding. Included in disclosed stricter sensitivity.'
        if idx == 9 and arm in [('qwen3','original'),('qwen3','coverage_check'),('qwen30b','original')]:
            row['reason'] += ' It subsequently emphasizes only When You Wish upon a Star. A conclusion-only reading would reject it; included in disclosed stricter sensitivity.'
        if idx == 12 and row['model'] == 'qwen30b':
            row['reason'] += ' Supporting movie names Hercules/Tarzan do not match the correct filtered movies. This is answer-count agreement only; included in disclosed stricter sensitivity.'
        if idx == 15 and arm == ('qwen25','coverage_check'):
            row['reason'] += ' Earlier prose inconsistently denies a matching record; final requested date is nevertheless explicit. Included in disclosed stricter sensitivity.'
    annotations.update(complete_domain=True,
        reviewer='One unblinded assistant; no independent human adjudication.',
        review_note='Apply the frozen requested-value SQL comparison to the entire final response. Correct labels do not certify explanatory claims. All nontrivial borderline decisions are explicit; a separate post-review conservative sensitivity is not substituted for the fixed audit.')
    out=root / 'research/evidence/vakra_expansion_disney_annotations_v1.json'
    with out.open('x',encoding='utf8') as f:
        json.dump(annotations,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'reviewed':len(annotations['rows']),'complete_domain':True,'complete_batch':False}))


if __name__ == '__main__':
    main()
