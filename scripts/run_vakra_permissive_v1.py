"""Fixed-prompt permissive executor sensitivity control on known tasks."""
from pathlib import Path
import json
import os
import subprocess
import time
import traceback

ROOT=Path('/xingjing/autoresearch-agent-papers')
REV=ROOT/'revisions/vakra-permissive-v1'
BATCH='vakra-permissive-v1'
DOMAINS=('computer_student','cars','book_publishing_company')


def main():
    output=ROOT/'runs'/BATCH
    marker=ROOT/'logs'/f'{BATCH}-process.json'
    if output.exists() or marker.exists():raise FileExistsError('Batch already registered')
    if json.loads((ROOT/'logs/vakra-crossdomain-v1-process.json').read_text())['status']!='complete':
        raise RuntimeError('Prior batch is not complete')
    if subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip():
        raise RuntimeError('GPU process present; refusing to share GPUs')
    selection=json.loads((REV/'protocol/selection.json').read_text())
    assert selection['registered_episodes']==240
    output.mkdir(parents=True)
    manifest=output/'grid_manifest.json'
    report={'batch':BATCH,'purpose':'post-outcome executor sensitivity on fixed prompts and known tasks; not independent confirmation or official score',
            'registered_episodes':240,'status':'running','started':time.time(),'workers':[],
            'selection':selection,'input_limit':32768,'conditions':['original','coverage_check']}
    children=[]
    try:
        env=dict(os.environ,PYTHONPATH=str(ROOT/'deps/vakra-v2')+':'+str(REV),
                 PYTHON_DOTENV_DISABLED='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',
                 OMP_NUM_THREADS='4',TOKENIZERS_PARALLELISM='false')
        for domain in DOMAINS:
            for gpu,(condition,model,name) in enumerate([
                ('original','qwen3','Qwen3-4B-Instruct-2507'),
                ('coverage_check','qwen3','Qwen3-4B-Instruct-2507'),
                ('original','qwen25','Qwen2.5-7B-Instruct'),
                ('coverage_check','qwen25','Qwen2.5-7B-Instruct')]):
                command=[str(ROOT/'.venv/bin/python'),'-m','autolab.vakra_native',
                    '--prepared',str(REV/'prepared'/domain),'--agent-source',str(REV/'upstream/agent_interface.py'),
                    '--model-path',str(ROOT/'models'/name),'--output',str(output/domain/condition/model/'shard-0'),
                    '--count','20','--shards','1','--shard','0','--max-steps','20',
                    '--max-new-tokens','512','--max-input-tokens','32768','--instruction-condition',condition,
                    '--call-policy','sequential','--max-tool-calls','20']
                with (ROOT/'logs'/f'{BATCH}-{domain}-{condition}-{model}.log').open('x') as log:
                    child=subprocess.Popen(command,cwd=REV,env=dict(env,CUDA_VISIBLE_DEVICES=str(gpu)),stdout=log,stderr=subprocess.STDOUT)
                record={'domain':domain,'gpu':gpu,'condition':condition,'model':model,
                        'pid':child.pid,'command':command,'started':time.time()}
                children.append((child,record));report['workers'].append(record)
            manifest.write_text(json.dumps(report,indent=2))
            deadline=time.monotonic()+7200
            while children:
                for child,record in list(children):
                    if child.poll() is not None:
                        record.update(exit_code=child.returncode,finished=time.time())
                        children.remove((child,record))
                        if child.returncode:raise RuntimeError(f'Worker failed: {record}')
                if time.monotonic()>deadline:raise TimeoutError('Two-hour domain-wave limit')
                if children:time.sleep(10)
            manifest.write_text(json.dumps(report,indent=2))
        report['status']='complete'
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


if __name__=='__main__':
    main()
