"""Resolve the unchanged memory study's original and restarted deployment bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def members(path):
    with zipfile.ZipFile(path) as z:
        names=z.namelist()
        if len(names)!=len(set(names)):
            raise ValueError('Duplicate ZIP member')
        return {name:z.read(name) for name in names}


def prepare(root=ROOT):
    ev=root/'research/evidence'
    inputs={name:(ev/name).read_bytes() for name in [
        'memory_test40_tie_registration_v1.json','memory_test40_tie_deployment_v1.json',
        'research_queue_restart_amendment_v2.json','research_queue_restart_deployment_v2.json']}
    reg,original,amendment,deployment=[json.loads(data) for data in inputs.values()]
    matched=[r for r in amendment['revisions'] if r['batch']=='tau-memory-test40-ties-v2']
    if len(matched)!=1:raise ValueError('Missing or duplicate memory restart')
    revision=matched[0]
    if revision['changed_existing_files'] or revision['original_revision']!=original['revision']:
        raise ValueError('Memory restart must preserve every original member')
    old_path=root/'results/deploy'/f"{revision['original_revision']}.zip"
    new_path=root/'results/deploy'/f"{revision['revision']}.zip"
    if digest(old_path.read_bytes())!=revision['original_archive_sha256'] or revision['original_archive_sha256']!=original['source_archive_sha256']:
        raise ValueError('Original deployment identity mismatch')
    if digest(new_path.read_bytes())!=revision['archive_sha256']:
        raise ValueError('Restarted archive identity mismatch')
    old,new=members(old_path),members(new_path)
    extra='scripts/restart_registered_queue_v2.py'
    if set(new)!=set(old)|{extra} or any(new[k]!=v for k,v in old.items()):
        raise ValueError('Restart changed original source or protocol bytes')
    if digest(new[extra])!=revision['supervisor_sha256']:
        raise ValueError('Restart supervisor differs')
    if new['protocol/registration.json']!=inputs['memory_test40_tie_registration_v1.json']:
        raise ValueError('Registered bytes differ from deployment')
    if any(digest(new[k])!=v for k,v in revision['preserved_protocol_files'].items()):
        raise ValueError('Preserved protocol hash differs')
    bundle_path=root/'results/deploy/research-queue-restart-v2.zip'
    bundle=members(bundle_path)
    if digest(bundle_path.read_bytes())!=amendment['bundle_sha256'] or deployment['bundle_sha256']!=amendment['bundle_sha256']:
        raise ValueError('Observed deployment refers to a different bundle')
    inner=json.loads(bundle['restart_amendment.json'])
    if inner!={k:v for k,v in amendment.items() if k not in ['bundle_sha256','bundle_bytes','bundle_members']}:
        raise ValueError('Bundled and external amendment differ')
    if any(bundle[revision['revision']+'/'+k]!=v for k,v in new.items()):
        raise ValueError('Standalone archive differs from deployed bundle')
    preflights=[r for r in deployment['remote_preflights'] if r['revision']==revision['revision']]
    processes=[r for r in deployment['processes'] if r['batch']==revision['batch']]
    if len(preflights)!=1 or preflights[0]['exit_code']!=0 or len(processes)!=1:
        raise ValueError('Missing unique successful deployment record')
    return dict(purpose=__doc__,batch=revision['batch'],registration_batch=reg['batch'],
                revision=revision['revision'],source_archive_sha256=revision['archive_sha256'],
                source_archive_bytes=new_path.stat().st_size,source_archive_members=len(new),
                original_archive_sha256=revision['original_archive_sha256'],
                original_members_preserved=len(old),only_added_member=extra,
                supervisor_sha256=revision['supervisor_sha256'],
                registration_sha256=digest(inputs['memory_test40_tie_registration_v1.json']),
                source_bank_sha256=reg['source_bank_sha256'],registered_episodes=560,
                bundle_sha256=amendment['bundle_sha256'],
                provenance_inputs_sha256={k:digest(v) for k,v in inputs.items()},
                preparation_source_sha256=digest(Path(__file__).read_bytes()),
                scope='Static deployment lineage only. No target outputs read; no claim of run completion.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();result=prepare()
    with a.output.open('x',encoding='utf8') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result))
