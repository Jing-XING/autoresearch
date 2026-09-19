"""Thirty planned static structural audits; no adaptive research or gold access."""
import argparse
from dataclasses import asdict
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time
from .research_units import SYSTEM
from .native_tool_agent import NativeTransformersModel

SETTINGS={'max_new_tokens':384,'max_input_tokens':16384,'calls_per_example':1}


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def run_one(model,item):
    messages=[{'role':'system','content':SYSTEM},
              {'role':'user','content':json.dumps(item,ensure_ascii=False,separators=(',',':'))}]
    row={'id':item['id'],'messages':messages,'settings':SETTINGS,'scored':False}
    start=time.monotonic()
    try:
        row['reply']=asdict(model.generate_tools(messages,[],SETTINGS['max_new_tokens']))
        row['status']='returned'
    except Exception as exc:
        row.update(status='generation_error',error_type=type(exc).__name__,error=str(exc))
    row['elapsed_seconds']=time.monotonic()-start
    return row


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('inputs','registration','model-path','model-reference','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();reg=json.loads(a.registration.read_bytes())
    if sha(a.inputs)!=reg['inputs_sha256']:raise ValueError('Input bytes changed')
    items=json.loads(a.inputs.read_bytes())
    if len(items)!=15 or [r['id'] for r in items]!=reg['input_ids']:raise ValueError('Input grid changed')
    if any(set(r)!={'id','reports'} for r in items):raise ValueError('Unexpected input fields')
    ref=json.loads(a.model_reference.read_bytes())
    files={p.name:sha(p) for p in sorted(a.model_path.iterdir())
           if p.is_file() and (p.suffix in ('.json','.jinja','.safetensors') or p.name=='merges.txt')}
    if files!=ref['model_files_sha256']:raise ValueError('Model checkpoint changed')
    a.output.mkdir(parents=True,exist_ok=False)
    module=Path(__file__).parent
    meta={'inputs_sha256':sha(a.inputs),'registration_sha256':sha(a.registration),
          'model_reference_sha256':sha(a.model_reference),'model_files_sha256':files,
          'input_ids':reg['input_ids'],'settings':SETTINGS,'seed':20260919,
          'decoder':'greedy_native_template_empty_tools',
          'source_sha256':{n:sha(module/n) for n in ['research_unit_pilot.py','research_units.py',
              'native_tool_agent.py','local_smoke.py','tool_agent.py']},
          'packages':{n:importlib.metadata.version(n) for n in ['torch','transformers','safetensors','accelerate']}}
    (a.output/'manifest.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    model=NativeTransformersModel(a.model_path,tool_prefix=False,max_input_tokens=SETTINGS['max_input_tokens'])
    placement=dict(model.runtime_placement)
    placement['hf_device_map']={k:str(v) for k,v in placement['hf_device_map'].items()}
    (a.output/'placement.json').write_text(json.dumps(placement,indent=2),encoding='utf-8')
    for i,item in enumerate(items):
        row=run_one(model,item)
        with (a.output/f'case-{i:03}.json').open('x',encoding='utf-8') as f:json.dump(row,f,indent=2)
        print(json.dumps({'index':i,'status':row['status']}),flush=True)


if __name__=='__main__':main()
