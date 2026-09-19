"""Derive fixed public development views from a pinned, executed risk archive."""
import argparse
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile
import numpy as np
from autolab.research_units import VIEWS, SYSTEM, account, build_example

ARCHIVE_SHA='b9b07c7f46eccf90a366262f1ae55905d7afd3e53bb4c69e2330a61bf8555c3d'


def prepare(archive,output):
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=ARCHIVE_SHA:
        raise ValueError('Original execution archive changed')
    with ZipFile(archive) as z:
        names=[n for n in z.namelist() if n.endswith('/output/components.npz')]
        if not names: names=[n for n in z.namelist() if n=='output/components.npz']
        if len(names)!=1:raise ValueError('Missing or ambiguous components')
        raw=z.read(names[0])
    with np.load(io.BytesIO(raw),allow_pickle=False) as data:
        components=data['components']
    if components.shape!=(2,12,4,4000,2) or not np.isfinite(components).all():
        raise ValueError('Saved component schema changed')
    inputs, gold, source_records = [], {}, {}
    # Fixed first three public pools, no outcome-dependent selection.
    for i in range(3):
        for view in VIEWS:
            item,origins=build_example(f'dev{i:02}',components[0,i,1,:24,:].tolist(),view)
            inputs.append(item)
            gold[item['id']]={'pool':f'dev{i:02}','view':view,'expected':account(item)}
            source_records[item['id']]=origins
    output.mkdir(parents=True,exist_ok=False)
    files={'inputs.json':inputs,'gold.json':gold,'origins.json':source_records}
    for name,value in files.items():
        (output/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    report={'scope':'Derived public structural-audit examples, not new experiments or held-out tasks',
            'archive_sha256':ARCHIVE_SHA,'components_member':names[0],
            'components_sha256':hashlib.sha256(raw).hexdigest(),'examples':len(inputs),
            'public_pools':['dev00','dev01','dev02'],'budget':100,'block':0,
            'seed_indices_used':list(range(24)),
            'system_prompt_sha256':hashlib.sha256(SYSTEM.encode()).hexdigest(),
            'files':{n:hashlib.sha256((output/n).read_bytes()).hexdigest() for n in files},
            'source_sha256':{n:hashlib.sha256(Path(n).read_bytes()).hexdigest() for n in
                ['autolab/research_units.py','scripts/prepare_research_unit_pilot_v1.py',
                 'research/research_unit_pilot_v1.md']},'model_calls':0}
    (output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(json.dumps(prepare(a.archive,a.output)))
