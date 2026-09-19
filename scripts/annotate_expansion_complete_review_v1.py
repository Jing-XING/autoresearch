"""Materialize all 120 hockey reviews and retain the prior 300 labels unchanged.

One unblinded assistant read every complete hockey response or its absence.
This script records that review, not automated semantic scoring.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):
    with p.open('x',encoding='utf-8') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')


def main():
    ev=ROOT/'research/evidence';archive=ROOT/'results/remote/vakra-expansion-v2-complete.zip'
    assert archive.stat().st_size==6097663 and sha(archive)=='2e59af3255513bea2933f61822ad39131fb33f8de59ad5b1b5b2e10be7c572f5'
    raw=archive.with_suffix('');batch=raw/'runs/vakra-expansion-v2'
    with ZipFile(archive) as z:
        assert len(z.namelist())==517 and z.testzip() is None
        for n in z.namelist():assert (raw/n).resolve().is_relative_to(raw.resolve()) and (raw/n).read_bytes()==z.read(n)
    grid=json.loads((batch/'grid_manifest.json').read_bytes())
    assert grid['status']=='complete' and len(grid['workers'])==24 and all(w['exit_code']==0 for w in grid['workers'])
    packet=json.loads((ROOT/'results/reviews/vakra-expansion-complete-v1/ice_hockey_draft.json').read_bytes())
    annotations=json.loads((ROOT/'results/reviews/vakra-expansion-complete-v1/annotation_template.json').read_bytes())
    key=lambda r:(r['domain'],r['uuid'],r['model'],r['condition'])
    old={};prior_hashes={}
    for domain in ('cookbook','disney','genes'):
        p=ev/f'vakra_expansion_{domain}_annotations_v1.json';prior_hashes[p.name]=sha(p)
        for row in json.loads(p.read_bytes())['rows']:
            assert key(row) not in old;old[key(row)]=row
    assert len(old)==300
    correct={('qwen3','original'):{4,14,16},('qwen3','coverage_check'):{4,7,12},
             ('qwen25','original'):{1,4},('qwen25','coverage_check'):{1},
             ('qwen30b','original'):{4,6,9,12},('qwen30b','coverage_check'):{4,6,14}}
    lookup={(t['card']['task_index'],a['model'],a['condition']):(t['card'],a) for t in packet for a in t['answers']}
    negative={
        0:'Does not provide all 129 requested player names: either only the first three or an incomplete long enumeration. Stating the total is not the complete requested list.',
        3:'Omits the complete mapping of twenty distinct players to heights. Returned prose/list gives only examples or repeated season heights without entity correspondence.',
        4:'Names Carter Trevisani instead of the frozen shortest Italian player Anthony Aquino.',
        6:'Does not give the required count 1209: reports 2171 or produces an unfinished list of weights without a final count.',
        9:'Reports zero right-shooters at the specified height instead of the frozen count two.',
        11:'Claims no Edmonton-born player instead of returning the frozen maximum height 193 cm.',
        12:'The explicit selected oldest player is wrong: Alexander Svitov or Maxim Sushinsky instead of Yegor Shastin. Merely including Yegor in an intermediate candidate list does not correct the conflicting final selection.',
        14:'Reports zero or fifteen instead of the frozen count 150.',
    }
    positive={1:'Names Lane Manson.',4:'Names Anthony Aquino.',6:'Gives 1209.',7:'Gives the only requested season, 2001-2002.',
              9:'Gives two right-shooters.',12:'Explicitly selects Yegor Shastin.',14:'Gives 150.',16:'Gives 73 inches, equivalent to the frozen 6-foot-1 value.'}
    reused=0
    for row in annotations['rows']:
        if row['domain']!='ice_hockey_draft':
            prior=old[key(row)]
            assert all(row[k]==prior[k] for k in ('source','source_sha256','task_index','interpretation_stratum','call_policy'))
            row.update(answer_label=prior['answer_label'],reason=prior['reason'],grounding_status=prior['grounding_status']);reused+=1;continue
        idx=row['task_index'];card,a=lookup[idx,row['model'],row['condition']]
        assert row['source']==a['source']
        if card['interpretation_stratum']=='ambiguous':
            assert idx in (2,8,10,13,15,17,18,19)
            row.update(answer_label='ambiguous',reason='Frozen pre-run ambiguity: '+card['ambiguity']+' Retain execution/cost independent of the response; termination: '+a['termination']+'.')
        elif a['final_answer'] is None:
            assert idx not in correct[row['model'],row['condition']]
            row.update(answer_label='no_answer',reason='No final answer; termination '+a['termination']+'. Retained in the fixed twelve-task denominator.')
        elif idx in correct[row['model'],row['condition']]:
            row.update(answer_label='correct',reason=positive[idx]+' Requested-value match only; explanation and evidence sufficiency are not independently scored.')
        else:row.update(answer_label='incorrect',reason=negative[idx])
    assert reused==300 and len(annotations['rows'])==420
    annotations.update(complete_batch=True,reviewer='One unblinded assistant; no independent human adjudication.',
        review_note='All120icehockey final responses/absences read; prior300labels retained byte-field-identically after source hash matching. Frozen21ambiguoustasks excluded from accuracy, retained in costs. No grounding labels.',
        prior_annotation_sha256=prior_hashes)
    ap=ev/'vakra_expansion_complete_annotations_v1.json';save(ap,annotations)
    ep=ev/'vakra_expansion_complete_grid_v1.json';sp=ev/'vakra_expansion_complete_answer_summary_v1.json'
    subprocess.run([sys.executable,'scripts/summarize_vakra_registered_answers.py','--root',str(batch),'--summary',str(ep),'--annotations',str(ap),'--output',str(sp)],cwd=ROOT,check=True)
    execution=json.loads(ep.read_bytes());hockey=[r for r in execution['rows'] if r['domain']=='ice_hockey_draft']
    receipt=dict(complete_batch=True,episodes=420,distinct_tasks=70,successful_worker_exits=24,
        archive=archive.relative_to(ROOT).as_posix(),archive_sha256=sha(archive),archive_bytes=archive.stat().st_size,archive_entries=517,
        extracted_bytes_verified=True,initial_prompt_pairs_verified=sum(p['initial_pairing_verified'] for p in execution['prompt_pairs']),
        prior_annotations_retained=300,new_hockey_reviews=120,
        labels=dict(Counter(r['answer_label'] for r in annotations['rows'])),
        hockey_labels=dict(Counter(r['answer_label'] for r in annotations['rows'] if r['domain']=='ice_hockey_draft')),
        hockey_terminations=dict(Counter(r['termination'] for r in hockey)),
        hockey_final_at_generation_ceiling=sum(r['final_at_generation_token_ceiling'] for r in hockey),
        evidence_sha256={p.name:sha(p) for p in (ep,ap,sp)},script_sha256=sha(Path(__file__)),
        transfer_note='First SHA transcription failed before transfer; wrong-hash bridge stopped. Correct SHA read in four chunks, exact archive transferred successfully. No experiment rerun.',
        limits='One unblinded assistant, fixed SQL interpretations, repeated tasks/checkpoints not independent population samples. No official benchmark or grounding score.')
    save(ev/'vakra_expansion_complete_raw_receipt_v1.json',receipt);print(json.dumps(receipt))


if __name__=='__main__':main()
