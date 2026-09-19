"""Run the 140 frozen curation prompts after the registered memory batch."""
import json
import os
from pathlib import Path
import subprocess
import time
import traceback

ROOT = Path('/xingjing/autoresearch-agent-papers')
BATCH = 'nk-prefix-curation-v1'
REV = ROOT / 'revisions' / BATCH


def main():
    output = ROOT / 'curations' / BATCH
    marker = ROOT / 'logs' / (BATCH + '-process.json')
    if output.exists() or marker.exists():
        raise FileExistsError('Immutable curation batch already exists')
    output.mkdir(parents=True)
    manifest = output / 'grid_manifest.json'
    report = {'batch': BATCH, 'status': 'waiting_for_dependencies', 'registered': time.time(),
              'expected_sources': 70, 'expected_curations': 140, 'workers': [],
              'target_episodes': 0, 'purpose': 'NK-schema adaptation, not upstream NK reproduction'}
    children = []
    try:
        manifest.write_text(json.dumps(report, indent=2))
        deadline = time.monotonic() + 43200
        while True:
            try:
                prior = json.loads((ROOT / 'logs/tau-memory-test40-ties-v1-process.json').read_bytes())['status']
            except (FileNotFoundError, json.JSONDecodeError):
                prior = 'pending'
            if prior == 'failed':
                raise RuntimeError('Preceding memory batch failed; preserve order for diagnosis')
            active = subprocess.check_output(['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader'], text=True)
            if prior in ('complete', 'completed_with_worker_failures') and not active.strip():
                break
            if time.monotonic() > deadline:
                raise TimeoutError('Twelve-hour dependency wait limit')
            time.sleep(10)
        report.update(status='running', started=time.time())
        env = dict(os.environ, PYTHONPATH=str(REV), PYTHON_DOTENV_DISABLED='1', HF_HUB_OFFLINE='1',
                   TRANSFORMERS_OFFLINE='1', OMP_NUM_THREADS='4', TOKENIZERS_PARALLELISM='false')
        for gpu in range(4):
            command = [str(ROOT / '.venv/bin/python'), '-m', 'autolab.nk_prefix_curation',
                       '--prepared', str(REV / 'prepared'),
                       '--model-path', str(ROOT / 'models/Qwen3-4B-Instruct-2507'),
                       '--expected-model-hashes', str(REV / 'protocol/model_files_sha256.json'),
                       '--output', str(output / f'shard-{gpu}'), '--shard', str(gpu), '--shards', '4']
            with (ROOT / 'logs' / f'{BATCH}-{gpu}.log').open('x') as log:
                child = subprocess.Popen(command, cwd=REV, env=dict(env, CUDA_VISIBLE_DEVICES=str(gpu)),
                                         stdout=log, stderr=subprocess.STDOUT)
            children.append(child)
            report['workers'].append({'gpu': gpu, 'pid': child.pid, 'command': command})
        manifest.write_text(json.dumps(report, indent=2))
        deadline = time.monotonic() + 7200
        while any(child.poll() is None for child in children):
            if time.monotonic() > deadline:
                raise TimeoutError('Two-hour curation execution limit')
            time.sleep(10)
        for child, record in zip(children, report['workers']):
            record['exit_code'] = child.returncode
        if any(child.returncode for child in children):
            raise RuntimeError('A curation worker failed; do not delete partial evidence')
        summaries = [json.loads((output / f'shard-{i}/summary.json').read_bytes()) for i in range(4)]
        rows = [r for s in summaries for r in s['rows']]
        expected = json.loads((REV / 'prepared/manifest.json').read_bytes())['rows']
        pairs = {(r['record_id'], r['condition']) for r in rows}
        if len(rows) != 140 or pairs != {(r['record_id'], r['condition']) for r in expected}:
            raise ValueError('Curation coverage mismatch')
        report.update(status='complete', outcomes={k: sum(s[k] for s in summaries)
                                                  for k in ('valid', 'invalid', 'generation_errors')})
    except Exception as exc:
        report.update(status='failed', error=str(exc), traceback=traceback.format_exc())
    finally:
        for child, record in zip(children, report['workers']):
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
            record['exit_code'] = child.returncode
        report['finished'] = time.time()
        manifest.write_text(json.dumps(report, indent=2))
        with marker.open('x') as handle:
            json.dump(report, handle, indent=2)
        print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
