"""Run all twelve prospectively selected output-budget sensitivity targets."""
import json
import os
from pathlib import Path
import subprocess
import time
import traceback

ROOT = Path('/xingjing/autoresearch-agent-papers')
REV = ROOT / 'revisions/vakra-output-budget-v1'
BATCH = 'vakra-output-budget-v1'


def main():
    output = ROOT / 'runs' / BATCH
    marker = ROOT / 'logs' / (BATCH + '-process.json')
    if output.exists() or marker.exists():
        raise FileExistsError('Batch already registered')
    output.mkdir(parents=True)
    manifest = output / 'grid_manifest.json'
    report = {'batch':BATCH, 'purpose':__doc__, 'status':'waiting_for_dependencies',
              'registered_episodes':12, 'registered':time.time(), 'workers':[],
              'targets':[{'domain':'cookbook','task_index':1}, {'domain':'ice_hockey_draft','task_index':0}],
              'max_new_tokens':8192, 'other_budgets':'unchanged from primary manifests',
              'initial_pairing':'complete initial messages, ordered schemas and preview must match before generation'}
    children = []
    env = dict(os.environ,PYTHONPATH=str(ROOT / 'deps/vakra-v2')+':'+str(REV),
               PYTHON_DOTENV_DISABLED='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',
               OMP_NUM_THREADS='4',TOKENIZERS_PARALLELISM='false')
    try:
        manifest.write_text(json.dumps(report,indent=2))
        deadline = time.monotonic()+43200
        while True:
            try:
                status = json.loads((ROOT / 'logs/vakra-expansion-v1-process.json').read_text())['status']
            except (FileNotFoundError,json.JSONDecodeError):
                status = 'pending'
            if status == 'failed':
                raise RuntimeError('Primary expansion failed; preserve registration for diagnosis')
            busy = subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True)
            if status == 'complete' and not busy.strip():
                break
            if time.monotonic()>deadline:
                raise TimeoutError('Twelve-hour dependency limit')
            time.sleep(10)
        report.update(status='running',started=time.time())
        for target in report['targets']:
            domain,index = target['domain'],target['task_index']
            waves = [[('0','qwen3','Qwen3-4B-Instruct-2507','original'),
                      ('1','qwen3','Qwen3-4B-Instruct-2507','coverage_check'),
                      ('2','qwen25','Qwen2.5-7B-Instruct','original'),
                      ('3','qwen25','Qwen2.5-7B-Instruct','coverage_check')],
                     [('0,1','qwen30b','Qwen3-30B-A3B-Instruct-2507','original'),
                      ('2,3','qwen30b','Qwen3-30B-A3B-Instruct-2507','coverage_check')]]
            for wave in waves:
                for devices,model,checkpoint,condition in wave:
                    command=[str(ROOT / '.venv/bin/python'),'-m','autolab.vakra_budget_replay',
                        '--primary-worker',str(ROOT / 'runs/vakra-expansion-v1' / domain / condition / model / 'shard-0'),
                        '--prepared',str(REV / 'prepared' / domain),
                        '--agent-source',str(REV / 'upstream/agent_interface.py'),
                        '--model-path',str(ROOT / 'models' / checkpoint),
                        '--output',str(output / domain / condition / model / 'shard-0'),
                        '--task-index',str(index),'--max-new-tokens','8192']
                    with (ROOT / 'logs' / f'{BATCH}-{domain}-{condition}-{model}.log').open('x') as log:
                        child=subprocess.Popen(command,cwd=REV,env=dict(env,CUDA_VISIBLE_DEVICES=devices),
                                               stdout=log,stderr=subprocess.STDOUT)
                    record={'domain':domain,'task_index':index,'model':model,'condition':condition,
                            'gpu_ids':devices,'pid':child.pid,'command':command,'started':time.time()}
                    children.append((child,record));report['workers'].append(record)
                manifest.write_text(json.dumps(report,indent=2))
                deadline=time.monotonic()+14400
                while children:
                    for child,record in list(children):
                        if child.poll() is not None:
                            record.update(exit_code=child.returncode,finished=time.time())
                            children.remove((child,record))
                    if time.monotonic()>deadline:
                        raise TimeoutError('Four-hour wave limit')
                    if children:time.sleep(10)
                manifest.write_text(json.dumps(report,indent=2))
        assert len(report['workers'])==12
        report['status']='complete' if all(w['exit_code']==0 for w in report['workers']) else 'completed_with_worker_failures'
    except Exception as exc:
        report.update(status='failed',error=str(exc),traceback=traceback.format_exc())
    finally:
        for child,record in children:
            if child.poll() is None:
                child.terminate()
                try:child.wait(timeout=20)
                except subprocess.TimeoutExpired:child.kill();child.wait()
            record.update(exit_code=child.returncode,finished=time.time())
        report['finished']=time.time()
        manifest.write_text(json.dumps(report,indent=2))
        with marker.open('x') as f:json.dump(report,f,indent=2)
        print(json.dumps(report),flush=True)


if __name__=='__main__':main()
