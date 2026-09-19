"""Queue the 560 registered test-split memory runs after current VAKRA controls."""
from collections import deque
import json
import os
from pathlib import Path
import subprocess
import time
import traceback

ROOT = Path('/xingjing/autoresearch-agent-papers')
BATCH = 'tau-memory-test40-ties-v1'
REV = ROOT / 'revisions/tau-memory-test40-ties-code-v2'


def main():
    output = ROOT / 'runs' / BATCH
    marker = ROOT / 'logs' / (BATCH + '-process.json')
    assert not output.exists() and not marker.exists()
    selection = json.loads((REV / 'protocol/registration.json').read_bytes())
    assert selection['registered_episodes'] == 560
    output.mkdir(parents=True)
    report = {'batch': BATCH, 'purpose': __doc__, 'status': 'waiting_for_dependencies',
              'registered_episodes': 560, 'registered': time.time(), 'selection': selection, 'workers': []}
    manifest = output / 'grid_manifest.json'
    env = dict(os.environ, PYTHONPATH=str(REV), PYTHON_DOTENV_DISABLED='1', HF_HUB_OFFLINE='1',
               TRANSFORMERS_OFFLINE='1', LITELLM_LOCAL_MODEL_COST_MAP='True', OMP_NUM_THREADS='4',
               TOKENIZERS_PARALLELISM='false',
               TAU2_DATA_DIR=str(ROOT / 'third_party/tau2-bench/tau2-bench/data'))
    running = {}
    try:
        manifest.write_text(json.dumps(report, indent=2))
        deadline = time.monotonic() + 43200
        while True:
            try:
                prior = json.loads((ROOT / 'logs/vakra-output-budget-v1-process.json').read_text())['status']
            except (FileNotFoundError, json.JSONDecodeError):
                prior = 'pending'
            if prior == 'failed':
                raise RuntimeError('Preceding batch failed; preserve registration for diagnosis')
            busy = subprocess.check_output(['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader'], text=True)
            if prior in ('complete', 'completed_with_worker_failures') and not busy.strip():
                break
            if time.monotonic() > deadline:
                raise TimeoutError('Twelve-hour dependency limit')
            time.sleep(10)
        queues = {}
        for gpu in range(4):
            paired = [('record_id', 'none')]
            for tie in selection['tie_orders']:
                conditions = ['full_metadata', 'boundary_aware']
                if gpu % 2:
                    conditions.reverse()
                paired.extend((tie, condition) for condition in conditions)
            queues[gpu] = deque(paired)
        report.update(status='running', started=time.time(), queue_order={str(k): list(v) for k, v in queues.items()})
        deadline = time.monotonic() + 21600
        while any(queues.values()) or running:
            if time.monotonic() > deadline:
                raise TimeoutError('Six-hour batch execution limit')
            for gpu in range(4):
                if gpu in running:
                    child, record = running[gpu]
                    if child.poll() is None:
                        continue
                    record.update(exit_code=child.returncode, finished=time.time())
                    del running[gpu]
                    if child.returncode:
                        raise RuntimeError('Worker failed: ' + repr(record))
                if not queues[gpu]:
                    continue
                tie, condition = queues[gpu].popleft()
                model = 'qwen3' if gpu < 2 else 'qwen25'
                checkpoint = 'Qwen3-4B-Instruct-2507' if gpu < 2 else 'Qwen2.5-7B-Instruct'
                shard = gpu % 2
                command = [str(ROOT / '.venv/bin/python'), '-m', 'autolab.tau2_tie_transfer',
                    '--model-path', str(ROOT / 'models' / checkpoint), '--model', model,
                    '--output', str(output / tie / condition / model / f'shard-{shard}'),
                    '--tau-repo', str(ROOT / 'third_party/tau2-bench/tau2-bench'),
                    '--registration', str(REV / 'protocol/registration.json'),
                    '--memory-bank', str(ROOT / 'memory-banks/train-qwen3-cut8-v2.json'),
                    '--condition', condition, '--tie-order', tie, '--shard', str(shard)]
                with (ROOT / 'logs' / f'{BATCH}-{tie}-{condition}-{model}-{shard}.log').open('x') as log:
                    child = subprocess.Popen(command, cwd=REV, env=dict(env, CUDA_VISIBLE_DEVICES=str(gpu)),
                                             stdout=log, stderr=subprocess.STDOUT)
                record = {'gpu': gpu, 'model': model, 'shard': shard, 'condition': condition,
                          'tie_order': tie, 'pid': child.pid, 'command': command, 'started': time.time()}
                report['workers'].append(record)
                running[gpu] = child, record
            manifest.write_text(json.dumps(report, indent=2))
            if running:
                time.sleep(10)
        assert len(report['workers']) == 28
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
                    child.kill(); child.wait()
            record.update(exit_code=child.returncode, finished=time.time())
        report['finished'] = time.time()
        manifest.write_text(json.dumps(report, indent=2))
        with marker.open('x') as f:
            json.dump(report, f, indent=2)
        print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
