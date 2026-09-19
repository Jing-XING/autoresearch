"""Independently recompute archived development controls using scalar arithmetic."""
import hashlib
import json
import math
from pathlib import Path
import statistics
import zipfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_SHA = '3fb82164e58c6cc0c23818dae6071a0b939c7d5b3b4387f8d22df85518a997f4'


def sha(data): return hashlib.sha256(data).hexdigest()


def require(value, message):
    if not value: raise ValueError(message)


def close(a, b):
    require(math.isclose(a, b, abs_tol=1e-12, rel_tol=1e-11), f'Arithmetic mismatch: {a} != {b}')


def main():
    archive = ROOT / 'results/remote/risk-development-controls-v1-results.zip'
    data = archive.read_bytes()
    require(sha(data) == ARCHIVE_SHA, 'Archive hash mismatch')
    package = json.loads((ROOT / 'research/evidence/risk_development_controls_package_v1.json').read_bytes())
    with zipfile.ZipFile(archive) as z:
        expected = {'deployment_manifest.json', 'execution.json', 'tests.stdout.txt', 'tests.stderr.txt',
                    'controls.stdout.txt', 'controls.stderr.txt', 'run/summary.json', 'run/trials.jsonl'}
        require(set(z.namelist()) == expected and len(z.namelist()) == 8, 'Archive inventory mismatch')
        payload = {name: z.read(name) for name in z.namelist()}
    require(json.loads(payload['deployment_manifest.json']) == package['manifest'], 'Deployment mismatch')
    for rel, row in package['manifest']['files'].items():
        content = (ROOT / rel).read_bytes()
        require(len(content) == row['bytes'] and sha(content) == row['sha256'], f'Local source differs: {rel}')
    execution = json.loads(payload['execution.json'])
    require([r['name'] for r in execution] == ['tests', 'controls'], 'Unexpected executions')
    require(all(r['returncode'] == 0 and not r['timeout'] for r in execution), 'Remote execution failed')
    report = json.loads(payload['run/summary.json'])
    require(sha(payload['run/trials.jsonl']) == report['raw_trials_sha256'], 'Raw hash mismatch')
    require(report['model_calls'] == report['hidden_grader_calls'] == 0, 'Unexpected model/grader calls')
    require(not report['external_connection_attempts'], 'External connection attempted')
    require(set(report['thread_settings'].values()) == {'1'}, 'Unexpected thread settings')
    for rel, digest in report['source_sha256'].items():
        require(sha((ROOT / rel).read_bytes()) == digest, 'Source hash mismatch')
    pools = [f'dev{i:02}' for i in range(12)]
    methods = ['uniform', 'surrogate_only', 'difference']
    budgets, seeds = [50, 100, 200, 400], list(range(2026091900, 2026091916))
    require(report['budgets'] == budgets and report['seeds'] == seeds, 'Grid mismatch')
    source = ROOT / 'results/third_party/autoresearch-exam-tasks/source'
    inputs = json.loads((ROOT / 'research/evidence/autoresearch_exam_public_assets_v1.json').read_bytes())['files']
    risk_files = {p: r['sha256'] for p, r in inputs.items()
                  if p.startswith('label-efficient-risk-estimator/environment/app/data/dev/')}
    require(report['public_input_sha256'] == risk_files, 'Input inventory mismatch')
    for rel, digest in risk_files.items(): require(sha((source / rel).read_bytes()) == digest, 'Input hash mismatch')
    cached = {}
    for pool in pools:
        directory = source / 'label-efficient-risk-estimator/environment/app/data/dev' / pool
        target, surrogate, labels = [np.load(directory / (n + '.npy'), allow_pickle=False)
                                     for n in ('target_probs', 'surrogate_probs', 'labels')]
        losses = [-math.log(float(target[i, int(labels[i])])) for i in range(len(labels))]
        proxies = [math.fsum(float(surrogate[i, c]) * -math.log(float(target[i, c]))
                            for c in range(2)) for i in range(len(labels))]
        cached[pool] = (labels, losses, proxies, math.fsum(losses)/len(losses), math.fsum(proxies)/len(proxies))
    rows = [json.loads(line) for line in payload['run/trials.jsonl'].splitlines()]
    indexed = {(r['pool'], r['budget'], r['seed'], r['method']): r for r in rows}
    expected_keys = {(p, b, s, m) for p in pools for b in budgets for s in seeds for m in methods}
    require(len(rows) == len(indexed) == 2304 and set(indexed) == expected_keys, 'Incomplete or duplicate grid')
    errors = {}; calls = 0
    for key, row in indexed.items():
        pool, budget, seed, method = key
        labels, losses, proxies, risk, proxy_mean = cached[pool]
        require(row['status'] == 'ok' and row['duration_seconds'] <= 5, 'Trial failure')
        require(row['label_calls'] == row['distinct_labels'] == len(row['queries']) == budget, 'Label accounting')
        permutation = np.random.default_rng(np.random.SeedSequence([seed, 7701])).permutation(len(labels))
        require(sha(permutation.astype('<i8').tobytes()) == row['permutation_sha256'], 'Permutation hash')
        sampled = np.random.default_rng(seed).choice(len(labels), budget, replace=False)
        original = permutation[sampled].tolist()
        require([q['index'] for q in row['queries']] == sampled.tolist(), 'Different sample')
        require([q['original_index'] for q in row['queries']] == original, 'Wrong original index')
        require([q['label'] for q in row['queries']] == [int(labels[i]) for i in original], 'Wrong observed label')
        close(row['true_risk'], risk)
        estimate = {'uniform': lambda: math.fsum(losses[i] for i in original)/budget,
                    'surrogate_only': lambda: proxy_mean,
                    'difference': lambda: proxy_mean + math.fsum(losses[i]-proxies[i] for i in original)/budget}[method]()
        error = (estimate-risk)**2
        close(row['estimate'], estimate); close(row['squared_error'], error)
        errors[key] = error; calls += budget
    cell_ratios = {m: [] for m in methods}
    for cell in report['cells']:
        pool, budget = cell['pool'], cell['budget']
        medians = {m: statistics.median(errors[pool, budget, s, m] for s in seeds) for m in methods}
        for method in methods:
            close(cell['median_squared_error'][method], medians[method])
            ratio = medians[method]/medians['uniform']
            close(cell['ratios'][method], ratio)
            require(cell['failures'][method] == 0, 'Failure count mismatch')
            cell_ratios[method].append(ratio)
    require(len(report['cells']) == 48 and len({(c['pool'], c['budget']) for c in report['cells']}) == 48, 'Cell inventory')
    ratios = {m: statistics.median(values) for m, values in cell_ratios.items()}
    for m in methods: close(report['median_cell_ratio'][m], ratios[m])
    require(report['trials'] == 2304 and report['failures'] == 0, 'Summary counts')
    result = dict(status='independently-recomputed', archive_sha256=ARCHIVE_SHA, archive_bytes=len(data),
                  archive_entries=8, trials=len(rows), label_calls=calls, failures=0,
                  median_cell_ratio=ratios,
                  difference_cells_below_uniform=sum(v < 1 for v in cell_ratios['difference']),
                  difference_cell_ratio_range=[min(cell_ratios['difference']), max(cell_ratios['difference'])],
                  runtime=dict(python=report['python'], numpy=report['numpy'], execution=execution),
                  freeze_commit='eae5e2f', package_sha256=package['sha256'],
                  verifier_sha256=sha(Path(__file__).read_bytes()),
                  members={n: dict(bytes=len(b), sha256=sha(b)) for n, b in payload.items()},
                  scope='Scalar offline audit of fixed public development controls. No new run, hidden benchmark reward, Agent result or novel estimator.',
                  deployment_note='First UI command failed Python parsing before any execution; quoting corrected before the sole actual deployment/run.')
    out = ROOT / 'research/evidence/risk_development_controls_reanalysis_v1.json'
    with out.open('x', encoding='utf8') as f: json.dump(result, f, indent=2); f.write('\n')
    copy = ROOT / 'research/evidence/risk_development_controls_summary_v1.json'
    with copy.open('xb') as f: f.write(payload['run/summary.json'])
    print(json.dumps({k: v for k, v in result.items() if k not in ('members', 'runtime')}))


if __name__ == '__main__': main()
