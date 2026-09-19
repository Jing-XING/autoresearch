"""Acquire only public development inputs for three CPU task interfaces."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path

from fetch_autoresearch_exam_task_specs import REPO, REV, TREE_SHA, ROOT, get

TASKS=('label-efficient-risk-estimator','shortest-valid-ci-l2-ece','carps-star-discrepancy-subset-select')


def main():
    tree_path=ROOT/'tree.json';assert hashlib.sha256(tree_path.read_bytes()).hexdigest()==TREE_SHA
    tree=json.loads(tree_path.read_bytes());assert not tree['truncated']
    rows=[r for r in tree['tree'] if r['type']=='blob' and any(r['path'].startswith(t+'/environment/app/') for t in TASKS)]
    assert rows and all('/tests/' not in r['path'] and '/hidden_data/' not in r['path'] and '/hints/' not in r['path'] for r in rows)
    assert sum(r['size'] for r in rows)<3_000_000
    def fetch(row):
        rel=row['path'];assert '..' not in Path(rel).parts and not Path(rel).is_absolute()
        target=ROOT/'source'/rel
        data=target.read_bytes() if target.exists() else get(f'https://raw.githubusercontent.com/{REPO}/{REV}/{rel}')
        assert len(data)==row['size'] and hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==row['sha']
        if not target.exists():
            target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as f:f.write(data)
        return rel,dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),git_blob=row['sha'])
    with ThreadPoolExecutor(max_workers=4) as pool:files=dict(pool.map(fetch,rows))
    result=dict(repository=REPO,revision=REV,tree_sha256=TREE_SHA,tasks=list(TASKS),files=files,
        selection='Deliberate feasibility sample: three CPU-only interfaces using small public arrays/generators and NumPy/SciPy. Not random/representative task selection, no new-method claim.',
        scope='Public environment/app assets only. Development labels/parameters are explicitly agent-visible in the original task. No hidden/intermediate/final evaluator inputs, tests, hints or solutions downloaded.',
        fetch_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        dependency_script_sha256=hashlib.sha256(Path('scripts/fetch_autoresearch_exam_task_specs.py').read_bytes()).hexdigest())
    with Path('research/evidence/autoresearch_exam_public_assets_v1.json').open('x',encoding='utf8') as f:
        json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({'files':len(files),'bytes':sum(v['bytes'] for v in files.values()),'tasks':list(TASKS)}))


if __name__=='__main__':main()
