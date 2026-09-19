"""Exact finite-public-pool control-variate headroom; not an agent experiment."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import statistics
import sys


def moments(loss, proxy):
    n = len(loss)
    if n < 2 or len(proxy) != n or not all(map(math.isfinite, [*loss, *proxy])):
        raise ValueError('Invalid finite population')
    ml, mh = statistics.mean(loss), statistics.mean(proxy)
    vl = math.fsum((x-ml)**2 for x in loss)/(n-1)
    vh = math.fsum((x-mh)**2 for x in proxy)/(n-1)
    cov = math.fsum((x-ml)*(h-mh) for x, h in zip(loss, proxy))/(n-1)
    c = cov/vh if vh else 0.0
    variances = {name: statistics.variance([x-k*h for x,h in zip(loss,proxy)])
                 for name,k in [('uniform',0.0),('difference',1.0),('oracle',c)]}
    if vl <= 0:
        raise ValueError('Zero uniform variance; ratio undefined')
    return dict(n=n, mean_loss=ml, mean_proxy=mh, loss_variance=vl,
                proxy_variance=vh, covariance=cov, oracle_coefficient=c,
                residual_variances=variances,
                mse_ratios={k:v/vl for k,v in variances.items()})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--protocol',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    import numpy as np
    attempts=[]
    def offline(event, values):
        if event=='socket.connect':
            attempts.append(str(values[1]));raise PermissionError('Offline diagnostic')
    sys.addaudithook(offline)
    sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
    manifest=args.root/'research/evidence/autoresearch_exam_public_assets_v1.json'
    spec=json.loads(manifest.read_bytes())
    assert spec['revision']=='7758e84af55f7666cbdcdd7192959f45b09827af'
    source=args.root/'results/third_party/autoresearch-exam-tasks/source'
    prefix='label-efficient-risk-estimator/environment/app/data/dev/'
    inputs={}
    for rel,r in spec['files'].items():
        if rel.startswith(prefix):
            path=source/rel
            assert path.stat().st_size==r['bytes'] and sha(path)==r['sha256']
            inputs[rel]=r['sha256']
    assert len(inputs)==48
    rows=[]
    for i in range(12):
        pool=f'dev{i:02}';base=source/prefix/pool
        target,surrogate,labels=[np.load(base/(k+'.npy'),allow_pickle=False)
                                 for k in ('target_probs','surrogate_probs','labels')]
        assert target.shape==surrogate.shape==(2000,2) and labels.shape==(2000,)
        assert np.isfinite(target).all() and (target>0).all() and (target<=1).all()
        assert np.isfinite(surrogate).all() and (surrogate>=0).all() and (surrogate<=1).all()
        assert np.allclose(target.sum(axis=1),1) and np.allclose(surrogate.sum(axis=1),1)
        assert ((labels>=0)&(labels<2)).all()
        loss=[-math.log(float(target[j,int(labels[j])])) for j in range(2000)]
        proxy=[math.fsum(float(surrogate[j,k])*(-math.log(float(target[j,k])))
                         for k in range(2)) for j in range(2000)]
        row=moments(loss,proxy);row['pool']=pool
        row['exact_mse']={str(b):{k:(1-b/row['n'])*v/b
                                  for k,v in row['residual_variances'].items()}
                          for b in [50,100,200,400]}
        row['oracle_relative_to_difference']=row['residual_variances']['oracle']/row['residual_variances']['difference'] if row['residual_variances']['difference'] else None
        rows.append(row)
    summary=dict(pools=12, difference_better_than_uniform=sum(r['mse_ratios']['difference']<1 for r in rows),
                 median_exact_mse_ratio={k:statistics.median(r['mse_ratios'][k] for r in rows)
                                         for k in ['uniform','difference','oracle']},
                 oracle_coefficient_range=[min(r['oracle_coefficient'] for r in rows),max(r['oracle_coefficient'] for r in rows)])
    report=dict(summary=summary,rows=rows,public_input_sha256=inputs,
                input_manifest_sha256=sha(manifest),source_sha256=sha(Path(__file__)),
                protocol_sha256=sha(args.protocol),python=platform.python_version(),numpy=np.__version__,
                model_calls=0,hidden_grader_calls=0,external_connection_attempts=attempts,
                scope='Full-label fixed-public-pool oracle for fixed-coefficient uniform-sampling class only; expected squared error, not median error or official reward.')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf8',newline='\n') as f:
        json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(summary));print('REPORT_SHA256',sha(args.output))


if __name__=='__main__':main()
