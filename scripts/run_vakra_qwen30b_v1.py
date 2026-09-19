"""Registered 120-episode capacity control after independent-model grid finishes."""
from pathlib import Path
import json
import os
import subprocess
import time
import traceback

ROOT = Path('/xingjing/autoresearch-agent-papers')
REV = ROOT / 'revisions/vakra-qwen30b-v1'
BATCH = 'vakra-qwen30b-v1'
DOMAINS = ('computer_student', 'cars', 'book_publishing_company')


def status(path):
    try:
        return json.loads(path.read_text())['status']
    except (FileNotFoundError, json.JSONDecodeError):
        return 'pending'


def main():
    output = ROOT / 'runs' / BATCH
    marker = ROOT / 'logs' / (BATCH + '-process.json')
    if output.exists() or marker.exists():
        raise FileExistsError('Batch already registered')
    output.mkdir(parents=True)
    manifest = output / 'grid_manifest.json'
    selection = json.loads((REV / 'protocol/selection.json').read_text())
    report = {'batch': BATCH, 'purpose': __doc__, 'status': 'waiting_for_dependencies',
              'registered_episodes': 120, 'registered': time.time(), 'workers': [], 'selection': selection}
    children = []
    env = dict(os.environ, PYTHONPATH=str(ROOT / 'deps/vakra-v2') + ':' + str(REV),
               PYTHON_DOTENV_DISABLED='1', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
               OMP_NUM_THREADS='6', TOKENIZERS_PARALLELISM='false')
    try:
        deadline = time.monotonic() + 14400
        manifest.write_text(json.dumps(report, indent=2))
        while True:
            prior = status(ROOT / 'logs/vakra-smollm3-v1-process.json')
            downloaded = status(ROOT / 'models/Qwen3-30B-A3B-Instruct-2507/download_status.json')
            if 'failed' in (prior, downloaded):
                raise RuntimeError('Dependency failure: ' + repr((prior, downloaded)))
            if prior == downloaded == 'complete':
                busy = subprocess.check_output(['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader'], text=True)
                if not busy.strip():
                    break
            if time.monotonic() > deadline:
                raise TimeoutError('Four-hour dependency wait limit')
            time.sleep(10)
        report.update(status='infrastructure_smoke', started=time.time())
        manifest.write_text(json.dumps(report, indent=2))
        with (ROOT / 'logs' / (BATCH + '-smoke.log')).open('x') as log:
            subprocess.run([str(ROOT / '.venv/bin/python'), str(REV / 'scripts/qwen30b_infrastructure_smoke.py'),
                            str(output / 'infrastructure_smoke.json')], cwd=REV,
                           env=dict(env, CUDA_VISIBLE_DEVICES='0,1'), stdout=log, stderr=subprocess.STDOUT,
                           timeout=1200, check=True)
        report.update(status='running', inference_started=time.time())
        for domain in DOMAINS:
            for gpu_ids, condition in [('0,1', 'original'), ('2,3', 'coverage_check')]:
                command = [str(ROOT / '.venv/bin/python'), '-m', 'autolab.vakra_native',
                    '--prepared', str(REV / 'prepared' / domain), '--agent-source', str(REV / 'upstream/agent_interface.py'),
                    '--model-path', str(ROOT / 'models/Qwen3-30B-A3B-Instruct-2507'),
                    '--output', str(output / domain / 'sequential' / condition / 'shard-0'),
                    '--count', '20', '--shards', '1', '--shard', '0', '--max-steps', '20',
                    '--max-new-tokens', '512', '--max-input-tokens', '32768', '--max-tool-calls', '20',
                    '--instruction-condition', condition, '--call-policy', 'sequential',
                    '--template-profile', 'standard', '--device-profile', 'two_gpu_balanced']
                with (ROOT / 'logs' / f'{BATCH}-{domain}-{condition}.log').open('x') as log:
                    child = subprocess.Popen(command, cwd=REV, env=dict(env, CUDA_VISIBLE_DEVICES=gpu_ids),
                                             stdout=log, stderr=subprocess.STDOUT)
                record = {'domain': domain, 'gpu_ids': gpu_ids, 'call_policy': 'sequential',
                          'condition': condition, 'pid': child.pid, 'command': command, 'started': time.time()}
                children.append((child, record)); report['workers'].append(record)
            manifest.write_text(json.dumps(report, indent=2))
            deadline = time.monotonic() + 14400
            while children:
                for child, record in list(children):
                    if child.poll() is not None:
                        record.update(exit_code=child.returncode, finished=time.time())
                        children.remove((child, record))
                        if child.returncode:
                            raise RuntimeError('Worker failure: ' + repr(record))
                if time.monotonic() > deadline:
                    raise TimeoutError('Four-hour domain-wave limit')
                if children:
                    time.sleep(10)
            manifest.write_text(json.dumps(report, indent=2))
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
                    child.kill(); child.wait()
            record.update(exit_code=child.returncode, finished=time.time())
        report['finished'] = time.time()
        manifest.write_text(json.dumps(report, indent=2))
        with marker.open('x') as f:
            json.dump(report, f, indent=2)
        print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
