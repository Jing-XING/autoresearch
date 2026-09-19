"""Materialize explicitly reviewed labels for the completed two-domain snapshot.

The assignments below were authored after reading every final answer against
the frozen cards. They are not inferred by substring matching or an LLM judge.
"""
import hashlib
import json
from pathlib import Path


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root = Path('results/remote/vakra-crossdomain-first160-v1/runs/vakra-crossdomain-v1')
    ep = Path('research/evidence')
    cp = ep / 'vakra_crossdomain_sql_cards_v1.json'
    pp = ep / 'vakra_crossdomain_answer_audit_policy_v1.json'
    policy = json.loads(pp.read_bytes())
    assert policy['sql_cards_sha256'] == sha(cp)
    conditions = [('qwen3','original'),('qwen3','coverage_check'),('qwen25','original'),('qwen25','coverage_check')]
    correct = {
        'computer_student': [{0,6,9,13} for _ in range(4)],
        'cars': [{1,3,4,5,7,9,10,11,13,17}, {0,1,2,3,4,5,7,8,9,10,11,13,14,15,17},
                 {0,1,2,10,11,14,15,17,18}, {0,1,2,10,11,15,16,17,18}],
    }
    notes = {
        'computer_student': {
            0:'Reports six professors, matching the requested course count.',
            1:'Does not enumerate the 82 nonconsecutive eligible course IDs; a range, partial preview or empty answer is not the requested complete list.',
            2:'Does not give the frozen glossary interpretation of eight Level_300 courses; answers are 50 or zero.',
            3:'Preidentified professor/teaching-scope ambiguity; none supplies the full reference ID set. No forced semantic label.',
            4:'Does not provide courses of the advisors of student 376. The task-local initialization witness limits attribution to the model.',
            5:'Reports absence instead of the 13 advisor IDs. The reference itself incorrectly lists student-side IDs; neither list is supplied.',
            6:'Reports Level_400, matching the requested teacher course level.',
            7:'Reports no matching professors instead of IDs 101, 179 and 234.',
            8:'Does not give eight Level_300 courses under the frozen glossary interpretation. Qwen3 expresses uncertainty; Qwen2.5 reports zero.',
            9:'Reports five people teaching course 11.',
            10:'Does not give three Faculty_eme teachers under the frozen glossary interpretation; final answers give 40 Faculty rows.',
            11:'Preidentified course-versus-assignment ambiguity; final answers zero or 102 do not match the reference 27. No forced semantic label.',
            12:'Does not identify 375, the requested faculty employee under the frozen interpretation.',
            13:'Answers yes and identifies Faculty status for the teacher of course 9.',
            14:'Preidentified course-count and faculty-scope ambiguity; no output gives the reference 27. No forced semantic label.',
            15:'Does not give the eight courses of the advisor of student 6. A partial unrelated course list or inability statement does not answer the query; initialization insufficiency limits attribution.',
            16:'Reports zero instead of 13 distinct advisors of third-year students.',
            17:'Names only 107, 213 and 290; omits 326, 373 and 375. Acknowledging unseen IDs does not complete the requested list.',
            18:'Gives Level_300 but only three of seven teacher IDs. The reference is separately defective; matching a subset containing 165 is not full semantic correctness.',
            19:'Does not provide professor 297 and Faculty_eme; misinterprets course level or reports absence.'},
        'cars': {
            0:'Correct target is plymouth fury gran sedan; Qwen3 original instead names dodge st. regis.',
            1:'Reports 78 cars satisfying the weight and price restrictions.',
            2:'Correct acceleration is 14.5; Qwen3 original instead gives 15.5.',
            3:'The base Ford Torino costs USD 20000. Qwen3 supplies this; Qwen2.5 concludes no matching record.',
            4:'Qwen3 gives USA for the requested car/year. Qwen2.5 produces no final answer.',
            5:'Qwen3 gives 45 models. Qwen2.5 produces no final answer.',
            6:'Final lists are incomplete relative to 187 distinct USA car names; repeated names do not replace missing models. Output-budget saturation needs separate trace reporting.',
            7:'Qwen3 supplies all three requested highest-priced names in order; Qwen2.5 produces no final answer.',
            8:'Correct years are 1970, 1971, 1972, 1973. Only Qwen3 with reminder lists them; other answers state absence.',
            9:'Qwen3 gives all 42 requested weights; Qwen2.5 produces no final answer.',
            10:'Reports maximum acceleration 21.7 for the restricted price range.',
            11:'Reports average USD 28982.18, compatible with the SQL value at the stated precision.',
            12:'Preidentified distinct-car versus production-row ambiguity. Where present, 102 matches the reference row count, not the alternative 70 distinct cars.',
            13:'Qwen3 gives USA. Qwen2.5 states it cannot find Chevrolet Malibu.',
            14:'Correct mpg is 14. Qwen3 original and Qwen2.5 reminder give 18; the other two give 14.',
            15:'Correct country is USA. Qwen3 original gives Europe; the other three give USA.',
            16:'Correct price is USD 20000. Only Qwen2.5 reminder supplies it; other outputs state absence or inability.',
            17:'Reports displacement 200 for the specified price.',
            18:'Qwen2.5 gives 1980, equivalent to model year 80 in the fixed data; Qwen3 does not provide a year.',
            19:'Preidentified fastest-car interpretation ambiguity. Qwen3 chooses Japan by fuel economy, unlike reference USA by horsepower; Qwen2.5 gives reference-compatible USA.'}
    }
    rows=[]
    for rule in policy['rows']:
        d,i=rule['domain'],rule['task_index']
        if d not in correct:continue
        for j,(m,c) in enumerate(conditions):
            rel=f'{d}/{c}/{m}/shard-0/case-{i:03d}.json'
            source=root/rel;raw=json.loads(source.read_bytes())
            assert raw['uuid']==rule['uuid']
            present=raw.get('final_answer') is not None
            ambiguous=rule['interpretation_stratum']=='ambiguous'
            label='ambiguous' if ambiguous else 'correct' if i in correct[d][j] else 'incorrect' if present else 'no_answer'
            reference='compatible' if label=='correct' else 'incompatible' if present else 'no_answer'
            if d=='cars' and i==12 and present:reference='compatible'
            if d=='cars' and i==19 and m=='qwen25':reference='compatible'
            assert label!='correct' or present
            reason=notes[d][i] if present else f"No final answer: {raw['termination']}. " + notes[d][i]
            rows.append({'domain':d,'task_index':i,'uuid':rule['uuid'],'model':m,'condition':c,
                         'source':rel,'source_sha256':sha(source),'interpretation_stratum':rule['interpretation_stratum'],
                         'answer_label':label,'reference_compatibility':reference,'reason':reason,
                         'grounding_status':'not_scored'})
    assert len(rows)==160
    result={'purpose':'partial-batch assistant-authored qualitative labels; not official or independent human evaluation',
            'complete_batch':False,'audit_cards_sha256':sha(cp),'audit_policy_sha256':sha(pp),
            'snapshot_archive_sha256':sha(Path('results/remote/vakra-crossdomain-first160-v1.zip')),
            'important_limit':'SQL interpretations use released field descriptions not added to agent prompts. Incorrect answers do not by themselves establish avoidable model failure or lack of grounding.',
            'rows':rows}
    with (ep/'vakra_crossdomain_first160_answer_annotations.json').open('x',encoding='utf-8') as f:
        json.dump(result,f,ensure_ascii=False,indent=2)
    print('Recorded 160 explicitly reviewed labels; full-batch audit remains pending.')


if __name__=='__main__':main()
