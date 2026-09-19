"""Prospective fixed-prompt domain expansion; no tuning against its outputs."""
from pathlib import Path
import json
import os
import subprocess
import time
import traceback

ROOT = Path('/xingjing/autoresearch-agent-papers')
REV = ROOT / 'revisions/vakra-expansion-v1'
BATCH = 'vakra-expansion-v1'


def main():
    output = ROOT / 'runs' / BATCH
    marker = ROOT / 'logs' / (BATCH + '-process.json')
    if output.exists() or marker.exists():
        raise FileExistsError('Immutable batch already registered')
    selection = json.loads((REV / 'protocol/selection.json').read_text())
    assert selection['registered_episodes'] == 420
    output.mkdir(parents=True)
    manifest = output / 'grid_manifest.json'
    report = {'batch': BATCH, 'purpose': __doc__, 'status': 'waiting_for_dependencies',
              'registered_episodes': 420, 'registered': time.time(), 'selection': selection, 'workers': []}
    children = []
    env = dict(os.environ, PYTHONPATH=str(ROOT / 'deps/vakra-v2') + ':' + str(REV),
               PYTHON_DOTENV_DISABLED='1', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
               OMP_NUM_THREADS='4', TOKENIZERS_PARALLELISM='false')
    try:
        deadline = time.monotonic() + 21600
        manifest.write_text(json.dumps(report, indent=2))
        while True:
            try:
                prior = json.loads((ROOT / 'logs/vakra-qwen30b-v1-process.json').read_text())['status']
            except (FileNotFoundError, json.JSONDecodeError):
                prior = 'pending'
            if prior == 'failed':
                raise RuntimeError('Preceding capacity batch failed; preserve this registration for diagnosis')
            busy = subprocess.check_output(['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader'], text=True)
            if prior == 'complete' and not busy.strip():
                break
            if time.monotonic() > deadline:
                raise TimeoutError('Six-hour dependency limit')
            time.sleep(10)
        report.update(status='running', started=time.time())
        for domain in selection['domains']:
            name = domain['domain']
            count = len(domain['selected_task_ids'])
            waves = [
                [('0', 'qwen3', 'Qwen3-4B-Instruct-2507', 'original', 'single_gpu'),
                 ('1', 'qwen3', 'Qwen3-4B-Instruct-2507', 'coverage_check', 'single_gpu'),
                 ('2', 'qwen25', 'Qwen2.5-7B-Instruct', 'original', 'single_gpu'),
                 ('3', 'qwen25', 'Qwen2.5-7B-Instruct', 'coverage_check', 'single_gpu')],
                [('0,1', 'qwen30b', 'Qwen3-30B-A3B-Instruct-2507', 'original', 'two_gpu_balanced'),
                 ('2,3', 'qwen30b', 'Qwen3-30B-A3B-Instruct-2507', 'coverage_check', 'two_gpu_balanced')]]
            for wave in waves:
                for devices, model, checkpoint, condition, profile in wave:
                    command = [str(ROOT / '.venv/bin/python'), '-m', 'autolab.vakra_native',
                        '--prepared', str(REV / 'prepared' / name), '--agent-source', str(REV / 'upstream/agent_interface.py'),
                        '--model-path', str(ROOT / 'models' / checkpoint),
                        '--output', str(output / name / condition / model / 'shard-0'),
                        '--count', str(count), '--shards', '1', '--shard', '0', '--max-steps', '20',
                        '--max-new-tokens', '512', '--max-input-tokens', '32768', '--max-tool-calls', '20',
                        '--instruction-condition', condition, '--call-policy', 'sequential',
                        '--template-profile', 'standard', '--device-profile', profile]
                    with (ROOT / 'logs' / f'{BATCH}-{name}-{condition}-{model}.log').open('x') as log:
                        child = subprocess.Popen(command, cwd=REV, env=dict(env, CUDA_VISIBLE_DEVICES=devices),
                                                 stdout=log, stderr=subprocess.STDOUT)
                    record = {'domain': name, 'model': model, 'condition': condition, 'gpu_ids': devices,
                              'device_profile': profile, 'selected_count': count, 'call_policy': 'sequential',
                              'command': command, 'pid': child.pid, 'started': time.time()}
                    children.append((child, record)); report['workers'].append(record)
                manifest.write_text(json.dumps(report, indent=2))
                deadline = time.monotonic() + 14400
                while children:
                    for child, record in list(children):
                        if child.poll() is not None:
                            record.update(exit_code=child.returncode, finished=time.time())
                            children.remove((child, record))
                            if child.returncode:
                                raise RuntimeError('Worker failed: ' + repr(record))
                    if time.monotonic() > deadline:
                        raise TimeoutError('Four-hour wave limit')
                    if children:
                        time.sleep(10)
                manifest.write_text(json.dumps(report, indent=2))
        assert len(report['workers']) == 24
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
