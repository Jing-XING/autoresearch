"""Export only a closed registered memory grid; never inspect partial outcomes.

This verifies closure and file coverage, not task correctness. Run the frozen
scientific analyzer after retrieval. All worker JSON bytes are preserved.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import time
from zipfile import ZipFile, ZIP_DEFLATED

BATCH='tau-memory-test40-ties-v2'
TIES=('record_id','alternative_1','alternative_2')
MODELS=('qwen3','qwen25')
ARMS=[('record_id','none')]+[(t,c) for t in TIES for c in ('full_metadata','boundary_aware')]
WORKERS={(t,c,m,s) for t,c in ARMS for m in MODELS for s in (0,1)}


def digest(data):return hashlib.sha256(data).hexdigest()


def closed_grid(root):
    raw=(root/'grid_manifest.json').read_bytes()
    try:grid=json.loads(raw)
    except json.JSONDecodeError:return None  # The existing supervisor rewrites this file in place.
    if grid.get('batch')!=BATCH:raise ValueError('Wrong batch')
    if grid.get('status')=='failed':raise ValueError('Experiment failed; export not launched')
    if grid.get('status')!='complete':return None
    workers=grid.get('workers',[])
    keys=[(w['tie_order'],w['condition'],w['model'],w['shard']) for w in workers]
    if len(keys)!=28 or set(keys)!=WORKERS or any(w.get('exit_code')!=0 for w in workers):
        raise ValueError('Closed grid has missing, extra, duplicate or failed workers')
    if grid.get('registered_episodes')!=560:raise ValueError('Wrong registered count')
    return raw


def inventory(root):
    expected={'grid_manifest.json'}
    simulations=0
    for tie,condition,model,shard in sorted(WORKERS):
        prefix=Path(tie)/condition/model/f'shard-{shard}'
        folder=root/prefix
        names={p.name for p in folder.iterdir() if p.is_file()}
        required={'manifest.json','config.json','summary.json'}
        for i in range(20):required.update({f'case-{i:03}-status.json',f'case-{i:03}-model-audit.json'})
        optional={f'case-{i:03}.json' for i in range(20)}
        if not required<=names or names-required-optional:raise ValueError('Worker inventory differs: '+str(prefix))
        simulations+=len(names&optional)
        expected.update((prefix/n).as_posix() for n in names)
    actual=set()
    for p in root.rglob('*'):
        if p.is_symlink():raise ValueError('Symlink in result directory')
        if p.is_file():actual.add(p.relative_to(root).as_posix())
    if actual!=expected:raise ValueError('Extra or missing batch member')
    return sorted(actual),simulations


def export(root,output):
    root=root.resolve()
    if output.resolve().is_relative_to(root):raise ValueError('Archive must be outside source tree')
    grid=closed_grid(root)
    if grid is None:raise ValueError('Refuse to read or package unfinished outcomes')
    paths,simulations=inventory(root)
    before={n:(root/n).stat() for n in paths}
    records={};prefix='runs/'+BATCH+'/'
    output.parent.mkdir(parents=True,exist_ok=True)
    # Exclusive creation retains any failed partial archive for explicit diagnosis.
    with ZipFile(output,'x',ZIP_DEFLATED,compresslevel=6) as z:
        for n in paths:
            p=root/n;raw=p.read_bytes();after=p.stat()
            if (before[n].st_size,before[n].st_mtime_ns)!=(len(raw),after.st_mtime_ns):
                raise ValueError('Result changed during export: '+n)
            name=prefix+n;z.writestr(name,raw)
            records[name]={'bytes':len(raw),'sha256':digest(raw)}
        if (root/'grid_manifest.json').read_bytes()!=grid:raise ValueError('Closure record changed')
        for n,stat in before.items():
            now=(root/n).stat()
            if (now.st_size,now.st_mtime_ns)!=(stat.st_size,stat.st_mtime_ns):raise ValueError('Source changed: '+n)
        manifest={'batch':BATCH,'registered_statuses':560,'registered_audits':560,
                  'simulation_files':simulations,'workers':28,'grid_sha256':digest(grid),
                  'exporter_sha256':digest(Path(__file__).read_bytes()),'members':records,
                  'scope':'Closed-run byte export; no scientific analysis or reexecution'}
        z.writestr('export_manifest.json',json.dumps(manifest,indent=2)+'\n')
    h=hashlib.sha256()
    with output.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return {'archive':str(output),'archive_sha256':h.hexdigest(),'archive_bytes':output.stat().st_size,
            'payload_members':len(records),'grid_sha256':digest(grid),'simulation_files':simulations,
            'registered_statuses':560,'registered_audits':560,'workers':28}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('root','output','receipt','completion-marker'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--wait-seconds',type=int,default=0)
    a=p.parse_args()
    if not 0<=a.wait_seconds<=36*3600:raise ValueError('Wait outside bound')
    if a.output.exists() or a.receipt.exists():raise FileExistsError('Immutable output exists')
    end=time.monotonic()+a.wait_seconds
    while True:
        grid=closed_grid(a.root)
        try:marker=a.completion_marker.read_bytes();marker_value=json.loads(marker)
        except (FileNotFoundError,json.JSONDecodeError):marker_value=None
        if grid is not None and marker_value is not None:
            if marker_value!=json.loads(grid):raise ValueError('Completion marker differs from final grid')
            break
        if time.monotonic()>=end:raise TimeoutError('Grid or completion marker pending; no outcomes read')
        time.sleep(min(15,max(0,end-time.monotonic())))
    receipt=export(a.root,a.output)
    receipt['completion_marker_sha256']=digest(marker)
    with a.receipt.open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps(receipt),flush=True)


if __name__=='__main__':main()
