"""Frozen 48-episode development control; no outcome-dependent retries."""
from pathlib import Path
import json
import os
import subprocess
import time
import traceback

ROOT = Path('/xingjing/autoresearch-agent-papers')
REV = ROOT / 'revisions/vakra-v3'
BATCH = 'vakra-coverage12-v1'


def main():
    output = ROOT / 'runs' / BATCH
    marker = ROOT / 'logs' / (BATCH + '-process.json')
    if output.exists() or marker.exists():
        raise FileExistsError('Batch already registered')
    if json.loads((ROOT / 'logs/vakra-native-first4-v1-process.json').read_text())['status'] != 'complete':
        raise RuntimeError('Prior development batch is not complete')
    if subprocess.check_output(['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader'], text=True).strip():
        raise RuntimeError('GPU processes still active; refusing to share GPUs')
    output.mkdir(parents=True)
    report = {'batch': BATCH, 'purpose': 'simple prompt development control, not confirmatory evidence',
              'registered_episodes': 48, 'status': 'running', 'started': time.time(), 'workers': [],
              'conditions': ['original', 'coverage_check'], 'input_limit': 32768}
    manifest = output / 'grid_manifest.json'
    children = []
    try:
        env = dict(os.environ, PYTHONPATH=str(ROOT / 'deps/vakra-v2') + ':' + str(REV),
                   PYTHON_DOTENV_DISABLED='1', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                   OMP_NUM_THREADS='4', TOKENIZERS_PARALLELISM='false')
        for gpu, (condition, model, name) in enumerate([
            ('original', 'qwen3', 'Qwen3-4B-Instruct-2507'),
            ('coverage_check', 'qwen3', 'Qwen3-4B-Instruct-2507'),
            ('original', 'qwen25', 'Qwen2.5-7B-Instruct'),
            ('coverage_check', 'qwen25', 'Qwen2.5-7B-Instruct'),
        ]):
            command = [str(ROOT / '.venv/bin/python'), '-m', 'autolab.vakra_native',
                       '--prepared', str(REV / 'prepared'), '--agent-source', str(REV / 'upstream/agent_interface.py'),
                       '--model-path', str(ROOT / 'models' / name), '--output',
                       str(output / condition / model / 'shard-0'), '--count', '12', '--shards', '1', '--shard', '0',
                       '--max-steps', '20', '--max-new-tokens', '512', '--max-input-tokens', '32768',
                       '--instruction-condition', condition]
            log = ROOT / 'logs' / f'{BATCH}-{condition}-{model}.log'
            with log.open('x') as handle:
                child = subprocess.Popen(command, cwd=REV, env=dict(env, CUDA_VISIBLE_DEVICES=str(gpu)),
                                         stdout=handle, stderr=subprocess.STDOUT)
            record = {'gpu': gpu, 'condition': condition, 'model': model, 'pid': child.pid,
                      'command': command, 'started': time.time()}
            children.append((child, record))
            report['workers'].append(record)
        manifest.write_text(json.dumps(report, indent=2))
        deadline = time.monotonic() + 7200
        while children:
            for child, record in list(children):
                if child.poll() is not None:
                    record.update(exit_code=child.returncode, finished=time.time())
                    children.remove((child, record))
                    if child.returncode:
                        raise RuntimeError(f'Worker failed: {record}')
            if time.monotonic() > deadline:
                raise TimeoutError('Two-hour batch limit reached')
            if children:
                time.sleep(10)
        report['status'] = 'complete'
    except Exception as exc:
        report.update(status='failed', error=str(exc), traceback=traceback.format_exc())
    finally:
        for child, record in children:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
            record.update(exit_code=child.returncode, finished=time.time())
        report['finished'] = time.time()
        manifest.write_text(json.dumps(report, indent=2))
        with marker.open('x') as handle:
            json.dump(report, handle, indent=2)
        print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
