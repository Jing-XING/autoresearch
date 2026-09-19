"""Verify the raw Disney package and disclose borderline-answer sensitivity.

No new model runs or labels for previously unreviewed answers are generated.
The conservative variant is explicitly post-review and is not preregistered.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from autolab.vakra_review_summary import summarize_review


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    evidence = ROOT / 'research/evidence'
    archive = ROOT / 'results/remote/vakra-expansion-v2-disney-complete.zip'
    expected = '291b6889a529231078d1afe3bedb827509608dc993f1ccea01af629fd97a100a'
    assert sha(archive) == expected and archive.stat().st_size == 1077140
    rawroot = archive.with_suffix('')
    with ZipFile(archive) as z:
        assert z.testzip() is None and len(z.infolist()) == 145
        assert sum(Path(n).name.startswith('case-') for n in z.namelist()) == 120
        for n in z.namelist():
            p = (rawroot/n).resolve()
            assert p.is_relative_to(rawroot.resolve()) and p.read_bytes() == z.read(n)
        snapshot = json.loads(z.read('runs/vakra-expansion-v2/grid_manifest.disney_snapshot.json'))
        workers = [w for w in snapshot['workers'] if w['domain'] == 'disney']
        assert len(workers) == 6 and all(w['exit_code'] == 0 for w in workers)
    names = ['vakra_expansion_disney_closed_grid_v1.json',
             'vakra_expansion_disney_annotations_v1.json',
             'vakra_expansion_disney_answer_summary_v1.json']
    execution, annotations, primary = [json.loads((evidence/n).read_bytes()) for n in names]
    rules_path = evidence / 'vakra_domain_expansion_sql_cards_v1.json'
    rules = [r for r in json.loads(rules_path.read_bytes())['cards'] if r['domain'] == 'disney']
    borderline = {
        (3,'qwen3','original'): 'Rating PG matches, but the truncated explanation attributes Turbo to The Incredibles and guesses.',
        (7,'qwen3','original'): 'Both distinct title values match; response separately enumerates two 101 Dalmatians release years.',
        (9,'qwen3','original'): 'Both songs explicitly present, but conclusion selects only one.',
        (9,'qwen3','coverage_check'): 'Both songs explicitly present, but conclusion selects only one.',
        (9,'qwen30b','original'): 'Both songs explicitly present, but conclusion selects only one.',
        (12,'qwen30b','original'): 'Count 2 matches, but supporting film names are wrong.',
        (12,'qwen30b','coverage_check'): 'Count 2 matches, but supporting film names are wrong.',
        (15,'qwen25','coverage_check'): 'Correct explicit final date despite inconsistent earlier denial of a matching record.',
    }
    alternate = deepcopy(annotations)
    changed = []
    for row in alternate['rows']:
        k = (row['task_index'],row['model'],row['condition'])
        if k not in borderline:
            continue
        assert row['answer_label'] == 'correct'
        raw = json.loads((rawroot/'runs/vakra-expansion-v2'/row['source']).read_bytes())
        changed.append(dict(task_index=k[0],model=k[1],condition=k[2],source=row['source'],
                            source_sha256=row['source_sha256'],final_answer=raw['final_answer'],
                            stricter_reason=borderline[k]))
        row['answer_label']='incorrect'
        row['reason']='Post-review stricter sensitivity: '+borderline[k]
    assert len(changed)==8
    alternate_summary = summarize_review(execution,alternate,rules,allow_closed_domain=True)
    sensitivity = {
        'purpose':'Post-review conservative sensitivity to eight disclosed response-level judgment calls. Not a replacement preregistered metric, blind adjudication, error prevalence estimate or formal grounding evaluation.',
        'rule':'Change all eight disclosed borderline correct labels to incorrect simultaneously; retain every other label, denominator, ambiguous mask, source hash and execution cost.',
        'primary_summary_sha256':sha(evidence/names[2]),
        'cards_sha256':sha(rules_path),
        'changed_answers':changed,
        'primary_groups':primary['groups'],
        'stricter_summary':alternate_summary,
        'limits':'Changing all selected cases together is not a bound over every possible human adjudication. Cases were identified by the same unblinded assistant during review; independent adjudication remains absent.',
        'script_sha256':sha(Path(__file__)),
    }
    sensitivity_path=evidence/'vakra_expansion_disney_review_sensitivity_v1.json'
    with sensitivity_path.open('x',encoding='utf8') as f:
        json.dump(sensitivity,f,ensure_ascii=False,indent=2);f.write('\n')
    receipt = {
        'scope':'Second completed domain of the registered 420-episode expansion. Full batch incomplete at this extraction.',
        'complete_batch':False,'complete_domain':True,'domain':'disney',
        'episodes':120,'distinct_tasks':20,'successful_worker_exits':6,
        'archive':archive.relative_to(ROOT).as_posix(),'archive_bytes':archive.stat().st_size,
        'archive_entries':145,'archive_sha256':expected,
        'deployment_archive_sha256':sha(ROOT/'results/deploy/vakra-expansion-v2.zip'),
        'all_120_extracted_records_byte_match_archive':True,
        'review':'One unblinded assistant read all120 full finals/absence. Two premarked ambiguous tasks retain12 executions/costs and are excluded from correctness. Six no-final episodes include four on an ambiguous task; two remain unsuccessful in the108 scored executions.',
        'labels':dict(Counter(r['answer_label'] for r in annotations['rows'])),
        'evidence_sha256':{p.name:sha(p) for p in [*(evidence/n for n in names),sensitivity_path]},
        'script_sha256':sha(Path(__file__)),
        'execution_note':'Initial annotation materialization failed on a missing explanation-dictionary entry for task8, before writing any annotation file; fixed the dictionary and then materialized the same manually assigned labels. No new model run.',
    }
    with (evidence/'vakra_expansion_disney_raw_receipt_v1.json').open('x',encoding='utf8') as f:
        json.dump(receipt,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'archive_verified':True,'labels':receipt['labels'],
        'stricter_counts':[(g['model'],g['condition'],g['correct']) for g in alternate_summary['groups']],
        'primary_pairs':[{k:r[k] for k in ('model','difference_percentage_points')} |
            {k:len(r[k]) for k in ('gains','losses','both_correct','both_unsuccessful')} for r in primary['paired']]}))


if __name__=='__main__':
    main()
