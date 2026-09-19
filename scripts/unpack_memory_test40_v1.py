"""Verify and relocate an immutable closed-run ZIP before scientific analysis."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
from zipfile import ZipFile
from scripts.archive_memory_test40_v1 import BATCH, closed_grid, inventory


def unpack(archive,expected_sha,destination):
    h=hashlib.sha256()
    with archive.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    if h.hexdigest()!=expected_sha:raise ValueError('Whole archive differs')
    if destination.exists():raise FileExistsError('Use an empty new destination')
    with ZipFile(archive) as z:
        names=z.namelist()
        if len(names)!=len(set(names)):raise ValueError('Duplicate ZIP member')
        manifest=json.loads(z.read('export_manifest.json'))
        if manifest['batch']!=BATCH or manifest['registered_statuses']!=560 or manifest['registered_audits']!=560 or manifest['workers']!=28:
            raise ValueError('Export scope differs')
        entries=manifest['members']
        if set(names)!=set(entries)|{'export_manifest.json'}:raise ValueError('Manifest coverage differs')
        prefix='runs/'+BATCH+'/'
        for name,record in entries.items():
            rel=PurePosixPath(name)
            if not name.startswith(prefix) or rel.is_absolute() or '..' in rel.parts or '\\' in name or ':' in name:
                raise ValueError('Unsafe archive member')
            if z.getinfo(name).file_size!=record['bytes']:raise ValueError('Size differs')
            data=z.read(name)
            if hashlib.sha256(data).hexdigest()!=record['sha256']:raise ValueError('Member hash differs')
        grid=entries[prefix+'grid_manifest.json']
        if grid['sha256']!=manifest['grid_sha256']:raise ValueError('Grid hash differs')
        destination.mkdir(parents=True,exist_ok=False)
        for name in entries:
            p=destination/name;p.parent.mkdir(parents=True,exist_ok=True)
            with p.open('xb') as f:f.write(z.read(name))
    root=destination/'runs'/BATCH
    if closed_grid(root) is None:raise ValueError('Not closed')
    paths,simulations=inventory(root)
    if len(paths)!=len(entries) or simulations!=manifest['simulation_files']:raise ValueError('Inventory differs')
    return {'status':'verified','root':str(root),'archive_sha256':expected_sha,
            'payload_members':len(paths),'simulation_files':simulations,
            'scientific_analysis_executed':False}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('archive','destination','receipt'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--sha256',required=True)
    a=p.parse_args()
    if a.receipt.exists():raise FileExistsError(a.receipt)
    result=unpack(a.archive,a.sha256,a.destination)
    with a.receipt.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result))
