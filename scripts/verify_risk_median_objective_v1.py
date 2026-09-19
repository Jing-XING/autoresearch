"""Recompute saved median controls and audit sampled components without runner imports."""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import statistics
import zipfile

import numpy as np


def digest(data):
    return hashlib.sha256(data).hexdigest()


def near(a,b):
    if not math.isclose(a,b,rel_tol=1e-11,abs_tol=2e-14):
        raise ValueError(f'Arithmetic disagreement: {a} versus {b}')


def verify(archive, expected_sha, root):
    if digest(archive.read_bytes()) != expected_sha:
        raise ValueError('Archive differs')
    with zipfile.ZipFile(archive) as z:
        names=z.namelist()
        expected={'scripts/analyze_risk_median_objective_v1.py','research/risk_median_objective_v1.md',
                  'output/components.npz','output/report.json','execution.json','stdout.txt','stderr.txt'}
        if len(names)!=7 or set(names)!=expected:
            raise ValueError('Archive inventory differs')
        data={n:z.read(n) for n in names}
    report=json.loads(data['output/report.json']);execution=json.loads(data['execution.json'])
    if execution['exit_code']!=0 or execution['source_commit']!='bf9f4ae0c395219b1c61f7c07525636a9c17aa01' or data['stderr.txt']:
        raise ValueError('Execution not clean')
    for n in ('scripts/analyze_risk_median_objective_v1.py','research/risk_median_objective_v1.md'):
        if digest(data[n]) != execution['source_sha256'][n] or data[n] != (root/n).read_bytes():
            raise ValueError('Frozen execution source differs')
    if report['source_sha256']!=digest(data['scripts/analyze_risk_median_objective_v1.py']) or report['protocol_sha256']!=digest(data['research/risk_median_objective_v1.md']):
        raise ValueError('Report provenance differs')
    if report['components_sha256']!=digest(data['output/components.npz']):
        raise ValueError('Raw components differ')
    with np.load(io.BytesIO(data['output/components.npz']),allow_pickle=False) as f:
        if f.files!=['components']:
            raise ValueError('Unexpected raw array')
        x=f['components']
    if x.shape!=(2,12,4,4000,2) or not np.isfinite(x).all():
        raise ValueError('Incomplete sample grid')
    if report['seed_starts']!=[202609200000,202609210000] or report['budgets']!=[50,100,200,400] or report['repeats']!=4000 or report['pool_budget_samples']!=384000:
        raise ValueError('Design differs')
    if report['model_calls'] or report['hidden_grader_calls'] or report['external_connection_attempts']:
        raise ValueError('Unexpected outside access')
    coeff=[i/20 for i in range(81)]
    if coeff!=report['coefficients'] or len(report['cells'])!=48:
        raise ValueError('Coefficient/cell grid differs')
    manifest_path=root/'research/evidence/autoresearch_exam_public_assets_v1.json'
    manifest=json.loads(manifest_path.read_bytes())
    if digest(manifest_path.read_bytes())!=report['input_manifest_sha256']:
        raise ValueError('Public input manifest differs')
    source=root/'results/third_party/autoresearch-exam-tasks/source'
    prefix='label-efficient-risk-estimator/environment/app/data/dev/'
    inputs={n:r['sha256'] for n,r in manifest['files'].items() if n.startswith(prefix)}
    if len(inputs)!=48 or inputs!=report['public_input_sha256']:
        raise ValueError('Public file inventory differs')
    for n,h in inputs.items():
        if digest((source/n).read_bytes())!=h:
            raise ValueError('Public file differs')
    scalar_medians=0; sampled_rechecks=0; max_component_error=0.
    for i in range(12):
        pool=source/prefix/f'dev{i:02}'
        target,surrogate,labels=[np.load(pool/(n+'.npy'),allow_pickle=False) for n in ('target_probs','surrogate_probs','labels')]
        loss=[-math.log(float(target[j,int(labels[j])])) for j in range(2000)]
        proxy=[math.fsum(float(surrogate[j,k])*-math.log(float(target[j,k])) for k in range(2)) for j in range(2000)]
        ml,mh=statistics.mean(loss),statistics.mean(proxy)
        dl,dh=[v-ml for v in loss],[v-mh for v in proxy]
        denom=math.fsum(v*v for v in dh)
        oracle=math.fsum(a*b for a,b in zip(dl,dh))/denom if denom else 0.
        for k,budget in enumerate(report['budgets']):
            row=report['cells'][i*4+k]
            if (row['pool'],row['budget'])!=(f'dev{i:02}',budget):
                raise ValueError('Cell ordering differs')
            curves=np.median((x[:,i,k,:,0,None]+x[:,i,k,:,1,None]*np.array(coeff))**2,axis=1)
            if not np.allclose(curves,row['grid_median_squared_error'],rtol=1e-11,atol=2e-14):
                raise ValueError('Coefficient curve differs')
            chosen=min(range(81),key=lambda j:float(curves[0,j]))
            if chosen!=row['selected_grid_index'] or coeff[chosen]!=row['selected_coefficient']:
                raise ValueError('Coefficient selection did not use selection block alone')
            for name,c in [('uniform',0.),('difference',1.),('mse_oracle',oracle),('selected_grid',coeff[chosen])]:
                control=row['controls'][name];near(c,control['coefficient'])
                variance=math.fsum((a-c*b)**2 for a,b in zip(dl,dh))/math.fsum(a*a for a in dl)
                near(variance,control['exact_expected_mse_ratio'])
                for block in (0,1):
                    med=statistics.median((float(a)+c*float(b))**2 for a,b in x[block,i,k])
                    near(med,control['median_squared_error'][block]);scalar_medians+=1
                    reference=statistics.median(float(a)**2 for a in x[block,i,k,:,0])
                    near(med/reference,control['ratio_to_uniform'][block])
            for block,first_seed in enumerate(report['seed_starts']):
                for j in (0,1999,3999):
                    seed=first_seed+j
                    permutation=np.random.default_rng(np.random.SeedSequence([seed,7701])).permutation(2000)
                    indices=permutation[np.random.default_rng(seed).choice(2000,budget,replace=False)]
                    values=[math.fsum(loss[int(a)] for a in indices)/budget-ml,
                            mh-math.fsum(proxy[int(a)] for a in indices)/budget]
                    for actual,recorded in zip(values,x[block,i,k,j]):
                        max_component_error=max(max_component_error,abs(actual-float(recorded)))
                        near(actual,float(recorded))
                    sampled_rechecks+=1
    for name,s in report['summary'].items():
        for block in (0,1):
            near(statistics.median(r['controls'][name]['ratio_to_uniform'][block] for r in report['cells']),s['median_cell_ratio'][block])
        count=sum(r['controls'][name]['median_squared_error'][1]<r['controls']['difference']['median_squared_error'][1] for r in report['cells'])
        if count!=s['evaluation_cells_better_than_difference']:
            raise ValueError('Improvement count differs')
    return dict(archive_sha256=expected_sha,members={n:digest(b) for n,b in data.items()},
        scalar_control_medians_verified=scalar_medians,grid_medians_recomputed=7776,
        sampled_component_pairs_replayed=sampled_rechecks,total_component_pairs=384000,
        maximum_component_absolute_difference=max_component_error,public_files_verified=48,
        verification_source_sha256=digest(Path(__file__).read_bytes()),summary=report['summary'],
        scope='All saved control medians and coefficient curves checked; 288 selected component pairs independently recomputed with scalar loss arithmetic. Same NumPy RNG for sample identities. No model or official grader execution; not all 384000 sample pairs regenerated.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',type=Path,required=True);p.add_argument('--sha256',required=True)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=verify(a.archive,a.sha256,a.root)
    with a.output.open('x',encoding='utf-8',newline='\n') as f:json.dump(r,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in r.items() if k!='members'}))
