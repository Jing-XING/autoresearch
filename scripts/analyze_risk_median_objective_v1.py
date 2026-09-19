"""Public median-error linear-control diagnostic; no agent or official grader."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time

import numpy as np

BUDGETS = (50, 100, 200, 400)
SEED_STARTS = (202609200000, 202609210000)
REPEATS = 4000
COEFFICIENTS = np.arange(81, dtype=float) / 20


def sampled_components(loss, proxy, budget, seed):
    """Each row is a population; two returned components encode e(c)=e(0)+c*d."""
    n = loss.shape[-1]
    permutation = np.random.default_rng(np.random.SeedSequence([seed, 7701])).permutation(n)
    indices = permutation[np.random.default_rng(seed).choice(n, budget, replace=False)]
    return np.stack((loss[..., indices].mean(axis=-1) - loss.mean(axis=-1),
                     proxy.mean(axis=-1) - proxy[..., indices].mean(axis=-1)), axis=-1)


def compare(components, coefficients, oracle_coefficient):
    if components.ndim != 3 or components.shape[0] != 2 or components.shape[-1] != 2:
        raise ValueError('Need two complete sample blocks')
    candidates = np.asarray(coefficients, dtype=float)
    if not np.isfinite(components).all() or not np.isfinite(candidates).all() or not np.isfinite(oracle_coefficient):
        raise ValueError('Non-finite candidate or error component')
    curves = np.median((components[:, :, 0, None] + components[:, :, 1, None] * candidates) ** 2, axis=1)
    winner = int(np.argmin(curves[0]))  # Selection block only; fixed ascending grid.
    controls = {}
    for name, c in [('uniform', 0.), ('difference', 1.), ('mse_oracle', oracle_coefficient), ('selected_grid', float(candidates[winner]))]:
        values = np.median((components[:, :, 0] + c * components[:, :, 1]) ** 2, axis=1)
        controls[name] = {'coefficient': float(c), 'median_squared_error': values.tolist()}
    denominators = controls['uniform']['median_squared_error']
    if min(denominators) <= 0:
        raise ValueError('Zero reference median; normalized score undefined')
    for value in controls.values():
        value['ratio_to_uniform'] = [x / d for x, d in zip(value['median_squared_error'], denominators)]
    return dict(selected_grid_index=winner, selected_coefficient=float(candidates[winner]),
                grid_median_squared_error=curves.tolist(), controls=controls)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'protocol', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    attempts = []
    def offline(event, args):
        if event == 'socket.connect':
            attempts.append(str(args[1]))
            raise PermissionError('Offline public diagnostic')
    sys.addaudithook(offline)
    manifest = a.root / 'research/evidence/autoresearch_exam_public_assets_v1.json'
    m = json.loads(manifest.read_bytes())
    if m['revision'] != '7758e84af55f7666cbdcdd7192959f45b09827af':
        raise ValueError('Public revision changed')
    source = a.root / 'results/third_party/autoresearch-exam-tasks/source'
    prefix = 'label-efficient-risk-estimator/environment/app/data/dev/'
    verified = {}
    for rel, record in m['files'].items():
        if rel.startswith(prefix):
            path = source / rel
            if sha(path) != record['sha256'] or path.stat().st_size != record['bytes']:
                raise ValueError('Public input differs: ' + rel)
            verified[rel] = record['sha256']
    if len(verified) != 48:
        raise ValueError('Missing public pool inputs')
    losses, proxies = [], []
    for i in range(12):
        pool = source / prefix / f'dev{i:02}'
        target, surrogate, labels = [np.load(pool / (k + '.npy'), allow_pickle=False) for k in ('target_probs', 'surrogate_probs', 'labels')]
        if target.shape != (2000, 2) or surrogate.shape != target.shape or labels.shape != (2000,):
            raise ValueError('Pool shape differs')
        if not (np.isfinite(target).all() and (target > 0).all() and (target <= 1).all() and
                np.isfinite(surrogate).all() and (surrogate >= 0).all() and (surrogate <= 1).all() and
                np.allclose(target.sum(1),1) and np.allclose(surrogate.sum(1),1) and ((labels >= 0) & (labels < 2)).all()):
            raise ValueError('Invalid probability/label input')
        logs = -np.log(target)
        losses.append(logs[np.arange(2000), labels])
        proxies.append((surrogate * logs).sum(axis=1))
    loss, proxy = np.array(losses), np.array(proxies)
    components = np.empty((2,12,4,REPEATS,2), dtype=np.float64)
    for block, first_seed in enumerate(SEED_STARTS):
        for j in range(REPEATS):
            for k, budget in enumerate(BUDGETS):
                components[block,:,k,j,:] = sampled_components(loss,proxy,budget,first_seed+j)
        print(json.dumps({'completed_block':block,'sampled_pool_budget_trials':12*4*REPEATS}),flush=True)
    raw = a.output / 'components.npz'
    np.savez_compressed(raw, components=components)
    cells = []
    for i in range(12):
        centered_l, centered_h = loss[i]-loss[i].mean(), proxy[i]-proxy[i].mean()
        denominator = float(np.dot(centered_h,centered_h))
        oracle = float(np.dot(centered_l,centered_h)/denominator) if denominator else 0.
        base_var = float(np.dot(centered_l,centered_l))
        if base_var <= 0:
            raise ValueError('Uniform variance is zero')
        for k,budget in enumerate(BUDGETS):
            row=compare(components[:,i,k,:,:],COEFFICIENTS,oracle)
            row.update(pool=f'dev{i:02}',budget=budget)
            for value in row['controls'].values():
                residual=centered_l-value['coefficient']*centered_h
                value['exact_expected_mse_ratio']=float(np.dot(residual,residual)/base_var)
            cells.append(row)
    names=('uniform','difference','mse_oracle','selected_grid')
    summary={name:{'median_cell_ratio':[float(np.median([r['controls'][name]['ratio_to_uniform'][s] for r in cells])) for s in (0,1)],
                   'evaluation_cells_better_than_difference':sum(r['controls'][name]['median_squared_error'][1]<r['controls']['difference']['median_squared_error'][1] for r in cells)} for name in names}
    report=dict(purpose=__doc__,cells=cells,summary=summary,coefficients=COEFFICIENTS.tolist(),budgets=list(BUDGETS),
        seed_starts=list(SEED_STARTS),repeats=REPEATS,pool_budget_samples=int(2*12*4*REPEATS),
        components_sha256=sha(raw),input_manifest_sha256=sha(manifest),public_input_sha256=verified,
        source_sha256=sha(Path(__file__)),protocol_sha256=sha(a.protocol),python=platform.python_version(),numpy=np.__version__,
        thread_settings={k:os.environ.get(k) for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS')},
        duration_seconds=time.monotonic()-start,model_calls=0,hidden_grader_calls=0,external_connection_attempts=attempts,
        limits=['Both blocks reuse public development pools; only sampling seeds differ.',
                'Selection block chooses coefficients; evaluation outcomes cannot change them.',
                'Full-label MSE oracle and full-label grid selection are not budgeted estimators or Agent policies.',
                'Monte Carlo median estimates and a fixed grid, not exact population medians or an unrestricted oracle bound.',
                'No official private seeds, grader, reward conversion or sandbox reproduced.'])
    with (a.output/'report.json').open('x',encoding='utf-8',newline='\n') as f:
        json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(summary),flush=True)


if __name__ == '__main__':
    main()
