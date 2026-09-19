"""Queue the 160 NK-schema target episodes after complete source curation."""
from collections import deque
import json
import os
from pathlib import Path
import subprocess
import time
import traceback

ROOT = Path('/xingjing/autoresearch-agent-papers')
BATCH = 'tau-nk-test40-v1'
REV = ROOT / 'revisions' / BATCH


def main():
    output = ROOT / 'runs' / BATCH
    marker = ROOT / 'logs' / (BATCH + '-process.json')
    bank = ROOT / 'memory-banks/nk-prefix-curation-v1.json'
    if output.exists() or marker.exists() or bank.exists():
        raise FileExistsError('Immutable NK target experiment already exists')
    registration = json.loads((REV / 'protocol/registration.json').read_bytes())
    if registration['registered_episodes'] != 160:
        raise ValueError('Unexpected target count')
    output.mkdir(parents=True)
    manifest = output / 'grid_manifest.json'
    report = {'batch': BATCH, 'status': 'waiting_for_dependencies', 'registered': time.time(),
              'registered_episodes': 160, 'registration': registration, 'workers': []}
    env = dict(os.environ, PYTHONPATH=str(REV), PYTHON_DOTENV_DISABLED='1', HF_HUB_OFFLINE='1',
               TRANSFORMERS_OFFLINE='1', LITELLM_LOCAL_MODEL_COST_MAP='True', OMP_NUM_THREADS='4',
               TOKENIZERS_PARALLELISM='false', TAU2_DATA_DIR=str(ROOT / 'third_party/tau2-bench/tau2-bench/data'))
    py = str(ROOT / '.venv/bin/python')
    running = {}
    try:
        manifest.write_text(json.dumps(report, indent=2))
        deadline = time.monotonic() + 43200
        while True:
            try:
                prior = json.loads((ROOT / 'logs/nk-prefix-curation-v1-process.json').read_bytes())['status']
            except (FileNotFoundError, json.JSONDecodeError):
                prior = 'pending'
            if prior == 'failed':
                raise RuntimeError('Source curation batch failed; preserve artifacts for diagnosis')
            busy = subprocess.check_output(['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader'], text=True)
            if prior == 'complete' and not busy.strip():
                break
            if time.monotonic() > deadline:
                raise TimeoutError('Twelve-hour dependency limit')
            time.sleep(10)
        curation_rev = ROOT / 'revisions/nk-prefix-curation-v1'
        command = [py, '-m', 'autolab.nk_prefix_bank', '--prepared', str(curation_rev / 'prepared'),
                   '--curation', str(ROOT / 'curations/nk-prefix-curation-v1'),
                   '--registration', str(REV / 'protocol/curation_registration.json'),
                   '--source-bank', str(ROOT / 'memory-banks/train-qwen3-cut8-v2.json'), '--output', str(bank)]
        with (ROOT / 'logs' / (BATCH + '-bank-build.log')).open('x') as log:
            subprocess.run(command, cwd=REV, env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=180)
        queues = {gpu: deque(['nk_schema', 'nk_schema_boundary'] if gpu % 2 == 0
                             else ['nk_schema_boundary', 'nk_schema']) for gpu in range(4)}
        report.update(status='running', started=time.time(), queue_order={str(k): list(v) for k, v in queues.items()})
        deadline = time.monotonic() + 14400
        while any(queues.values()) or running:
            if time.monotonic() > deadline:
                raise TimeoutError('Four-hour target execution limit')
            for gpu in range(4):
                if gpu in running:
                    child, record = running[gpu]
                    if child.poll() is None:
                        continue
                    record.update(exit_code=child.returncode, finished=time.time())
                    del running[gpu]
                    if child.returncode:
                        raise RuntimeError('Target worker failed: ' + repr(record))
                if not queues[gpu]:
                    continue
                condition = queues[gpu].popleft()
                model = 'qwen3' if gpu < 2 else 'qwen25'
                checkpoint = 'Qwen3-4B-Instruct-2507' if gpu < 2 else 'Qwen2.5-7B-Instruct'
                shard = gpu % 2
                command = [py, '-m', 'autolab.tau2_nk_transfer', '--model-path', str(ROOT / 'models' / checkpoint),
                           '--model', model, '--output', str(output / condition / model / f'shard-{shard}'),
                           '--tau-repo', str(ROOT / 'third_party/tau2-bench/tau2-bench'),
                           '--registration', str(REV / 'protocol/registration.json'),
                           '--selection', str(REV / 'protocol/selection.json'), '--memory-bank', str(bank),
                           '--condition', condition, '--shard', str(shard)]
                with (ROOT / 'logs' / f'{BATCH}-{condition}-{model}-{shard}.log').open('x') as log:
                    child = subprocess.Popen(command, cwd=REV, env=dict(env, CUDA_VISIBLE_DEVICES=str(gpu)),
                                             stdout=log, stderr=subprocess.STDOUT)
                record = {'gpu': gpu, 'model': model, 'shard': shard, 'condition': condition,
                          'pid': child.pid, 'command': command, 'started': time.time()}
                report['workers'].append(record)
                running[gpu] = child, record
            manifest.write_text(json.dumps(report, indent=2))
            if running:
                time.sleep(10)
        if len(report['workers']) != 8:
            raise ValueError('Incomplete target worker grid')
        report['status'] = 'complete'
    except Exception as exc:
        report.update(status='failed', error=str(exc), traceback=traceback.format_exc())
    finally:
        for child, record in running.values():
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
        with marker.open('x') as f:
            json.dump(report, f, indent=2)
        print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
