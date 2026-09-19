"""Validate public development schemas and execute the unchanged CI generator.

No candidate optimizer, model, reward function, hidden inputs or official grader.
Run on the designated Linux compute host; local file acquisition is separate.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    source=root/'results/third_party/autoresearch-exam-tasks/source'
    manifests=[root/'research/evidence'/n for n in ('autoresearch_exam_task_specs_v1.json','autoresearch_exam_public_assets_v1.json')]
    inputs={};metadata=[]
    for p in manifests:
        d=json.loads(p.read_bytes());metadata.append(d)
        assert d['revision']=='7758e84af55f7666cbdcdd7192959f45b09827af'
        for rel,row in d['files'].items():
            assert '/tests/' not in rel and '/hidden_data/' not in rel and '/hints/' not in rel
            target=(source/rel).resolve();assert target.is_relative_to(source.resolve())
            assert target.stat().st_size==row['bytes'] and sha(target)==row['sha256']
            inputs[rel]=row['sha256']
    attempts=[]
    def guard(event,values):
        if event=='socket.connect':
            attempts.append(str(values[1]));raise PermissionError('Public input preflight is offline')
    sys.addaudithook(guard)
    import numpy as np
    risk_root=source/'label-efficient-risk-estimator/environment/app/data/dev'
    risk=[]
    for directory in sorted(risk_root.iterdir()):
        assert directory.is_dir()
        meta=json.loads((directory/'meta.json').read_bytes())
        n,c=meta['n_pool'],meta['n_classes'];assert (n,c)==(2000,2)
        for name in ('target_probs','surrogate_probs'):
            arr=np.load(directory/(name+'.npy'),allow_pickle=False)
            assert arr.shape==(n,c) and arr.dtype==np.float64 and arr.flags.c_contiguous
            assert np.isfinite(arr).all() and (arr>=0).all() and (arr<=1).all()
            assert np.allclose(arr.sum(axis=1),1,atol=1e-12,rtol=1e-12)
        labels=np.load(directory/'labels.npy',allow_pickle=False)
        assert labels.shape==(n,) and labels.dtype==np.int64 and ((labels>=0)&(labels<c)).all()
        risk.append(dict(pool=directory.name,n=n,classes=c))
    assert len(risk)==12
    carps_root=source/'carps-star-discrepancy-subset-select/environment/app/data/examples'
    manifest=json.loads((carps_root/'manifest.json').read_bytes());assert manifest['dim']==3
    clouds=[]
    for row in manifest['instances']:
        p=(carps_root/row['file']).resolve();assert p.is_relative_to(carps_root.resolve())
        arr=np.load(p,allow_pickle=False)
        assert arr.shape==(row['n'],3) and arr.dtype==np.float64 and arr.flags.c_contiguous
        assert np.isfinite(arr).all() and ((arr>=0)&(arr<=1)).all()
        assert 800<=row['n']<=4000 and row['k'] in (30,50,65) and row['k']<row['n']
        clouds.append(dict(id=row['id'],n=row['n'],k=row['k']))
    assert len(clouds)==8
    ci_root=source/'shortest-valid-ci-l2-ece/environment/app'
    module_spec=importlib.util.spec_from_file_location('official_public_panel',ci_root/'panel.py')
    module=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(module)
    draws=json.loads((ci_root/'data/dev_panel.json').read_bytes())['draws']
    settings=[r for draw in draws for r in draw['settings']]
    assert len(draws)==3 and len(settings)==24
    ci=[];calls=0
    for i,spec in enumerate(settings):
        assert spec['K'] in (2,3,5,10,50) and spec['k'] in (1,2,3) and spec['k']<spec['K']
        assert spec['n'] in (200,500,2000,10000) and len(spec['theta_grid'])==41
        seed=20260919+i;theta=spec['theta_grid'][20]
        first=module.draw_replication(spec,theta,np.random.default_rng(seed));calls+=1
        second=module.draw_replication(spec,theta,np.random.default_rng(seed));calls+=1
        assert all(np.array_equal(x,y) for x,y in zip(first,second))
        z,y=first;n,k=spec['n'],spec['K']
        assert z.shape==(n,k) and z.dtype==np.float64 and z.flags.c_contiguous
        assert np.isfinite(z).all() and ((z>=0)&(z<=1)).all()
        assert np.allclose(z.sum(axis=1),1,atol=1e-12,rtol=1e-12)
        assert y.shape==(n,) and y.dtype==np.int64 and ((y>=0)&(y<k)).all()
        ci.append(dict(id=spec['id'],n=n,K=k,k=spec['k'],seed=seed,grid_index=20,identical_seed_replay=True))
    assert not attempts
    result=dict(status='public-input-preflight-passed',revision=metadata[0]['revision'],
        files_verified=len(inputs),input_manifest_sha256={p.name:sha(p) for p in manifests},
        script_sha256=sha(Path(__file__)),python=sys.version,numpy=np.__version__,
        risk_pools=risk,clouds=clouds,ci_settings=ci,ci_generator_calls=calls,
        external_connection_attempts=attempts,model_calls=0,grader_calls=0,
        scope='Public development inputs and generator API only. No Agent policy evaluation, task score, confidence-interval coverage study, hidden test access, Docker reproduction or new method result. NumPy may differ from original per-task pinned environments.')
    with args.output.open('x',encoding='utf8') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:result[k] for k in ('status','files_verified','numpy','ci_generator_calls','model_calls','grader_calls')}))


if __name__=='__main__':main()
