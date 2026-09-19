"""Record reviewed publishing answers and merge the unchanged 160 prior labels."""
import hashlib
import json
from pathlib import Path


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    evidence=Path('research/evidence')
    template=Path('results/vakra-crossdomain-review-v1/annotation_template.json')
    previous_path=evidence/'vakra_crossdomain_first160_answer_annotations.json'
    result=json.loads(template.read_bytes());previous=json.loads(previous_path.read_bytes())
    for k in ('audit_cards_sha256','audit_policy_sha256'):assert previous[k]==result[k]
    keys=lambda r:(r['domain'],r['condition'],r['model'],r['uuid'])
    earlier={keys(r):r for r in previous['rows']}
    root=Path('results/remote/vakra-crossdomain-v1/runs/vakra-crossdomain-v1')
    correct={('qwen3','original'):{0,2,3,5,6,7,9,10,11,12,13,15,16,17,18},
             ('qwen3','coverage_check'):{0,2,3,6,9,10,11,12,13,15,16,17,18},
             ('qwen25','original'):{11,12,13,14,17,18},
             ('qwen25','coverage_check'):{3,4,11,12,13,14,15,17}}
    notes={
        0:'Correct title is Onions, Leeks, and Garlic. Qwen3 names it; Qwen2.5 original reports no 1992 orders.',
        1:'No answer provides a maximum-royalty title paired with its correct lower range. Stress at range zero is not valid for royalty 24; its correct lower range is 14001. Qwen3 original ends without the requested title/range pair.',
        2:'Qwen3 lists all eleven employee-name pairs. Qwen2.5 lists only the first three, omitting eight.',
        3:'Where a final answer is present, it correctly names Yoshi Latimer and 1989-06-11.',
        4:'The requested CEO is Philip Cramer, hired 1989-11-11. Only Qwen2.5 reminder supplies that answer. It conflicts with the released CFO reference, which is retained separately.',
        5:'Correct title is Computer Phobic AND Non-Phobic Individuals: Behavior Variations. Only Qwen3 original supplies it. Qwen3 reminder associates the maximum price with the wrong title.',
        6:'Qwen3 provides all five employee/job pairs, including Maria Pontes as Publisher and Matti Karttunen as Managing Editor.',
        7:'Qwen3 original lists all seventeen distinct title/sales pairs with harmless duplicate authorship rows. Qwen3 reminder lists only three pairs. Qwen2.5 original swaps sales for Silicon Valley Gastronomic Treats and Straight Talk About Computers; reminder omits titles and misaligns several sales values.',
        8:'Correct CA/noncontract title is You Can Combat Computer Stress! Qwen3 original supplies a different title and reminder incorrectly treats CA as an absent city.',
        9:'Qwen3 reports the correct six USA publishers. Qwen2.5 reports three.',
        10:'Qwen3 supplies Annette, Diego, Matti and Victoria. Qwen2.5 original names different employees; reminder omits Victoria.',
        11:'The requested highest attainable job level is 100. The answer field matches, although matching employee job_lvl is not itself proof of checking jobs.max_lvl.',
        12:'The requested book price is correctly 10.95. References to an individual 75-unit order do not establish the SQL aggregate sales total 108; answer correctness is kept separate from grounding.',
        13:'Correctly gives USA for the publisher of Life Without Fear.',
        14:'Correct publisher is Algodata Infosystems. Qwen2.5 supplies it; Qwen3 incorrectly gives Binnet & Hardley.',
        15:'Correct distinct-publisher count is three. Qwen3 and Qwen2.5 reminder give it; Qwen2.5 original gives eight. Correct count is not a validation of every auxiliary title/price association in the explanation.',
        16:'Qwen3 correctly gives mod_cook. Qwen2.5 has no final answer.',
        17:'Correct requested royalty is 24. A dollar sign on YTD quantity in Qwen2.5 original is an auxiliary unit error and is not used to validate grounding.',
        18:'Correct job level is 100. Qwen3 and Qwen2.5 original supply it; Qwen2.5 reminder incorrectly states absence.',
        19:'Does not give F-C16315M under the frozen highest-job-level SQL interpretation. The phrase highest employee is underspecified; alternative employee-ID interpretations are a post-outcome ambiguity observation, not a retrospective exclusion.'}
    rows=[]
    for item in result['rows']:
        key=keys(item)
        if key in earlier:
            assert item['source_sha256']==earlier[key]['source_sha256']==sha(root/item['source'])
            rows.append(earlier[key]);continue
        assert item['domain']=='book_publishing_company'
        i=item['task_index'];m=item['model'];c=item['condition']
        raw=json.loads((root/item['source']).read_bytes())
        assert raw['uuid']==item['uuid'] and sha(root/item['source'])==item['source_sha256']
        present=raw.get('final_answer') is not None
        label='correct' if i in correct[(m,c)] else 'incorrect' if present else 'no_answer'
        assert label!='correct' or present
        reference='compatible' if label=='correct' else 'incompatible' if present else 'no_answer'
        if i==4 and present:reference='incompatible'
        item.update(answer_label=label,reference_compatibility=reference,
                    reason=notes[i] if present else f"No final answer: {raw['termination']}. "+notes[i])
        rows.append(item)
    assert len(rows)==240 and all(r['answer_label']!='pending' for r in rows)
    result.update(purpose='complete assistant-authored qualitative SQL audit, not official VAKRA score or independent human annotation',
                  complete_batch=True,prior_annotations_sha256=sha(previous_path),rows=rows,
                  reference_compatibility_definition='Compatibility with the complete reference answer after requested name/ID entity resolution and order normalization; not mere substring overlap or literal JSON equality.',
                  post_outcome_observations=[{'domain':'book_publishing_company','task_index':19,
                    'observation':'Highest employee can be read as highest employee ID rather than highest job level. Keep the frozen SQL-primary label and denominator; do not describe the 55-task subtotal as unambiguously specified.'}],
                  important_limit=previous['important_limit'])
    output=evidence/'vakra_crossdomain_v1_answer_annotations.json'
    with output.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print('Recorded 240 labels; preserved all prior 160 labels and frozen primary denominator.')


if __name__=='__main__':main()
