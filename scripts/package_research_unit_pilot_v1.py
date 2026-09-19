"""Package only public display inputs, pinned model references and frozen code."""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    prep=Path('results/preparations/research-unit-pilot-v1')
    m=json.loads((prep/'manifest.json').read_bytes())
    if sha(prep/'inputs.json')!=m['files']['inputs.json']:raise ValueError('Changed prepared input')
    source=['autolab/'+n+'.py' for n in ['__init__','runner','tool_agent','local_smoke',
        'native_tool_agent','research_units','research_unit_pilot']]
    source+=['scripts/run_research_unit_pilot_v1.py','research/research_unit_pilot_v1.md']
    contents={n:Path(n).read_bytes() for n in source}
    contents['inputs/pilot.json']=(prep/'inputs.json').read_bytes()
    references=json.loads(Path('research/evidence/hotpot_pilot_registration_v1.json').read_bytes())['model_references']
    for model,ref in references.items():contents['protocol/'+model+'.json']=json.dumps(ref,indent=2).encode()
    reg={'batch':'research-unit-pilot-v1','registered_episodes':30,'examples':15,
         'models':['qwen3','qwen25'],'input_ids':[r['id'] for r in json.loads(contents['inputs/pilot.json'])],
         'inputs_sha256':m['files']['inputs.json'],'preparation_manifest_sha256':sha(prep/'manifest.json'),
         'protocol_sha256':sha(Path('research/research_unit_pilot_v1.md')),
         'model_references':references,'predecessor':'hotpot-pilot-v1',
         'gold_deployed':False,'scope':'Static public-development unit audit, not an adaptive research-agent evaluation'}
    contents['protocol/registration.json']=json.dumps(reg,indent=2).encode()
    hashes={n:hashlib.sha256(b).hexdigest() for n,b in sorted(contents.items())}
    contents['package_files.json']=json.dumps(hashes,indent=2).encode()
    path=Path('results/deploy/research-unit-pilot-v1.zip')
    with ZipFile(path,'x',ZIP_DEFLATED) as z:
        for n,b in sorted(contents.items()):
            if any(x in n for x in ['.env','gold.json','origins.json']):raise ValueError(n)
            z.writestr(n,b)
    report=dict(reg,archive_sha256=sha(path),archive_bytes=path.stat().st_size,
                archive_members=len(contents),files_sha256=hashes)
    with Path('research/evidence/research_unit_pilot_registration_v1.json').open('x',encoding='utf-8') as f:
        json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({k:report[k] for k in ('archive_sha256','archive_bytes','archive_members')}))


if __name__=='__main__':main()
