"""Record the unblinded assistant review of all sixty frozen genes responses.

Labels were assigned after reading every complete final response/absence. This
materializes that review; it is not an automated semantic scorer.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, content):
    with path.open('x', encoding='utf8') as f:
        json.dump(content, f, ensure_ascii=False, indent=2); f.write('\n')


def main():
    evidence = ROOT / 'research/evidence'
    archive = ROOT / 'results/remote/vakra-expansion-v2-genes-complete.zip'
    digest = '994a33d9cfeb6516798a109ae264cdac4c4f3796bd1044343e3d0d0214938ac0'
    assert sha(archive) == digest and archive.stat().st_size == 534302
    rawroot = archive.with_suffix('')
    with ZipFile(archive) as z:
        assert z.testzip() is None and len(z.namelist()) == 85
        assert sum(Path(n).name.startswith('case-') for n in z.namelist()) == 60
        for n in z.namelist():
            p = (rawroot/n).resolve()
            assert p.is_relative_to(rawroot.resolve()) and p.read_bytes() == z.read(n)
        snapshot = json.loads(z.read('runs/vakra-expansion-v2/grid_manifest.genes_snapshot.json'))
        workers = [w for w in snapshot['workers'] if w['domain'] == 'genes']
        assert len(workers) == 6 and all(w['exit_code'] == 0 for w in workers)
    review = json.loads((ROOT/'results/reviews/vakra-expansion-genes-v1/genes.json').read_bytes())
    annotations = json.loads((ROOT/'results/reviews/vakra-expansion-genes-v1/annotation_template.json').read_bytes())
    by_identity = {(t['card']['task_index'], a['model'], a['condition']): (t['card'], a)
                   for t in review for a in t['answers']}
    for row in annotations['rows']:
        idx = row['task_index']; arm = (row['model'], row['condition'])
        card, answer = by_identity[idx, *arm]
        assert row['source'] == answer['source']
        if idx in (0, 1, 2, 5, 6, 8, 9):
            assert card['interpretation_stratum'] == 'ambiguous'
            row['answer_label'] = 'ambiguous'
            row['reason'] = ('Frozen pre-run ambiguity: ' + card['ambiguity'] +
                             ' Excluded from answer accuracy independently of response; execution/cost retained. Termination: ' + answer['termination'] + '.')
        else:
            assert idx in (3, 4, 7) and answer['final_answer'] is not None
            row['answer_label'] = 'incorrect'
            if idx == 3:
                if arm in (('qwen3', 'coverage_check'), ('qwen25', 'coverage_check')):
                    reason = 'Claims an empty set, whereas the frozen query returns 52 distinct GeneIDs.'
                else:
                    reason = 'Names only G234108 and G234368, sometimes with a repeated ID and an unspecified remainder. This does not provide the requested complete set of 52 distinct GeneIDs. Row totals or unnamed other identifiers are not a complete answer.'
            elif idx == 4:
                reason = 'Reports 954 or 1034 instead of the frozen count of 184 distinct non-essential GeneIDs in the nucleus. Annotation-row counts do not satisfy the distinct-gene interpretation.'
            elif arm == ('qwen3', 'original'):
                reason = 'Omits PROTEIN SYNTHESIS and adds ENERGY; the fixed minimum-pair functions require the three specified values.'
            elif arm == ('qwen3', 'coverage_check'):
                reason = 'Gives only the transport function for G237467 and declares G235331 functions unavailable, omitting both CELLULAR ORGANIZATION and PROTEIN SYNTHESIS.'
            elif arm == ('qwen25', 'coverage_check'):
                reason = 'Assigns the transport function to both genes, omitting the two required G235331 functions.'
            else:
                reason = 'Lists transport and cellular organization but omits the additional PROTEIN SYNTHESIS function for G235331. The frozen card requires the complete union or per-gene sets.'
            row['reason'] = reason
    assert Counter(r['answer_label'] for r in annotations['rows']) == {'ambiguous': 42, 'incorrect': 18}
    annotations.update(complete_domain=True, reviewer='One unblinded assistant; no independent human adjudication.',
                       review_note='All sixty full final responses or absences read. Seven pre-run ambiguous tasks remain excluded; all eighteen scored answers fail the fixed requested-value interpretation. No formal grounding labels or prevalence claim.')
    annotation_path = evidence/'vakra_expansion_genes_annotations_v1.json'
    save(annotation_path, annotations)
    execution_path = evidence/'vakra_expansion_genes_closed_grid_v1.json'
    summary_path = evidence/'vakra_expansion_genes_answer_summary_v1.json'
    subprocess.run([sys.executable, 'scripts/summarize_vakra_registered_answers.py',
                    '--root', str(rawroot/'runs/vakra-expansion-v2'), '--summary', str(execution_path),
                    '--annotations', str(annotation_path), '--closed-domain', 'genes',
                    '--output', str(summary_path)], cwd=ROOT, check=True)
    execution = json.loads(execution_path.read_bytes())
    receipt = dict(scope='Third completed domain of the registered expansion; hockey and full420 remain incomplete at extraction.',
                   complete_batch=False, complete_domain=True, domain='genes', episodes=60, distinct_tasks=10,
                   successful_worker_exits=6, archive=archive.relative_to(ROOT).as_posix(), archive_bytes=534302,
                   archive_entries=85, archive_sha256=digest, all_extracted_files_byte_match_archive=True,
                   deployment_archive_sha256=sha(ROOT/'results/deploy/vakra-expansion-v2.zip'),
                   initial_prompt_pairs=30, labels=dict(Counter(r['answer_label'] for r in annotations['rows'])),
                   final_answers=sum(r['final_answer'] is not None for r in execution['rows']),
                   final_at_generation_ceiling=sum(r['final_at_generation_token_ceiling'] for r in execution['rows']),
                   terminations=dict(Counter(r['termination'] for r in execution['rows'])),
                   evidence_sha256={p.name: sha(p) for p in (execution_path, annotation_path, summary_path)},
                   script_sha256=sha(Path(__file__)),
                   limits='Three scored tasks per condition, all zero correct. This floor cannot establish equivalence or general prompt ineffectiveness. One unblinded assistant review; no independent adjudication.')
    save(evidence/'vakra_expansion_genes_raw_receipt_v1.json', receipt)
    print(json.dumps(receipt))


if __name__ == '__main__': main()
