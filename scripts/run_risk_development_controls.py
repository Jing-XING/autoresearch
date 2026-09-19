"""Run frozen trusted risk baselines on public development pools, not hidden tests."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autolab.risk_development import BASELINES, BUDGETS, SEEDS, evaluate, summarize
import numpy as np


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    source = ROOT / 'results/third_party/autoresearch-exam-tasks/source'
    inputs = ROOT / 'research/evidence/autoresearch_exam_public_assets_v1.json'
    manifest = json.loads(inputs.read_bytes())
    if manifest['revision'] != '7758e84af55f7666cbdcdd7192959f45b09827af':
        raise ValueError('Unexpected source revision')
    verified = {}
    for rel, record in manifest['files'].items():
        if rel.startswith('label-efficient-risk-estimator/environment/app/data/dev/'):
            path = source / rel
            if sha(path) != record['sha256'] or path.stat().st_size != record['bytes']:
                raise ValueError(f'Input mismatch: {rel}')
            verified[rel] = record['sha256']
    if len(verified) != 48:
        raise ValueError('Expected twelve public pools with four files each')
    attempts = []
    def offline(event, values):
        if event == 'socket.connect':
            attempts.append(str(values[1]))
            raise PermissionError('Public development controls are offline')
    sys.addaudithook(offline)
    data = source / 'label-efficient-risk-estimator/environment/app/data/dev'
    pools = [f'dev{i:02}' for i in range(12)]
    if sorted(p.name for p in data.iterdir()) != pools:
        raise ValueError('Unexpected pool inventory')
    rows = []
    with (args.output / 'trials.jsonl').open('x', encoding='utf8') as stream:
        for pool in pools:
            arrays = [np.load(data / pool / (name + '.npy'), allow_pickle=False)
                      for name in ('target_probs', 'surrogate_probs', 'labels')]
            for budget in BUDGETS:
                for seed in SEEDS:
                    for method, factory in BASELINES.items():
                        row = evaluate(factory, *arrays, budget, seed)
                        row.update(pool=pool, method=method)
                        stream.write(json.dumps(row, allow_nan=False, separators=(',', ':')) + '\n')
                        stream.flush()
                        rows.append(row)
    report = summarize(rows, pools)
    report.update(scope='Public development baselines only; not official benchmark rewards or an Agent-method result.',
                  source_revision=manifest['revision'], python=platform.python_version(), numpy=np.__version__,
                  seeds=list(SEEDS), budgets=list(BUDGETS), public_input_sha256=verified,
                  external_connection_attempts=attempts, model_calls=0, hidden_grader_calls=0,
                  thread_settings={k: os.environ.get(k) for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')},
                  source_sha256={str(p.relative_to(ROOT)).replace('\\', '/'): sha(p) for p in
                                 (Path(__file__), ROOT / 'autolab/risk_development.py',
                                  ROOT / 'research/risk_development_controls_v1.md', inputs)},
                  raw_trials_sha256=sha(args.output / 'trials.jsonl'))
    with (args.output / 'summary.json').open('x', encoding='utf8') as f:
        json.dump(report, f, indent=2, allow_nan=False)
        f.write('\n')
    print(json.dumps({k: report[k] for k in ('trials', 'failures', 'median_cell_ratio')}))
    if attempts or report['failures'] or any(v is None for v in report['median_cell_ratio'].values()):
        raise SystemExit(2)


if __name__ == '__main__':
    main()
