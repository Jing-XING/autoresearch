"""Pin all public task specifications without downloading held-out evaluators."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import tomllib
import urllib.request

REPO='bespokelabsai/AutoResearchExam'
REV='7758e84af55f7666cbdcdd7192959f45b09827af'
TREE_SHA='6811bc0e676d0ce9962d170cfc729ac23598ceae0407936addc831fb35cbf6d0'
ROOT=Path('results/third_party/autoresearch-exam-tasks')


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'research-task-feasibility'}),timeout=40).read()


def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    tree_path=ROOT/'tree.json'
    if not tree_path.exists():tree_path.write_bytes(get(f'https://api.github.com/repos/{REPO}/git/trees/{REV}?recursive=1'))
    assert hashlib.sha256(tree_path.read_bytes()).hexdigest()==TREE_SHA
    tree=json.loads(tree_path.read_bytes());assert not tree['truncated']
    entries=[r for r in tree['tree'] if r['type']=='blob']
    tasks=sorted(r['path'].split('/')[0] for r in entries if r['path'].endswith('/task.toml'))
    assert len(tasks)==len(set(tasks))==29
    selected={'README.md','LICENSE','CITATION.cff','citation.bib'}
    selected.update(t+'/'+suffix for t in tasks for suffix in
        ('README.md','instruction.md','task.toml','environment/Dockerfile','environment/requirements.txt'))
    rows=[r for r in entries if r['path'] in selected]
    def fetch(row):
        rel=row['path'];assert '/tests/' not in rel and '/hints/' not in rel and '..' not in Path(rel).parts
        target=ROOT/'source'/rel
        data=target.read_bytes() if target.exists() else get(f'https://raw.githubusercontent.com/{REPO}/{REV}/{rel}')
        assert len(data)==row['size'] and hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==row['sha']
        if not target.exists():
            target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as f:f.write(data)
        return rel,dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),git_blob=row['sha'])
    with ThreadPoolExecutor(max_workers=4) as pool:files=dict(pool.map(fetch,rows))
    specs=[]
    for task in tasks:
        rel=task+'/task.toml';spec=tomllib.loads((ROOT/'source'/rel).read_text(encoding='utf8'))
        specs.append(dict(task=task,task_toml_sha256=files[rel]['sha256'],spec=spec))
    result=dict(repository=REPO,revision=REV,tree_sha256=TREE_SHA,
        scope='All29 public task specifications and public setup/instruction documents; no tests, hidden data, hints, solutions or task model execution.',
        repository_total_blobs=len(entries),repository_total_blob_bytes=sum(r['size'] for r in entries),
        files=files,task_specs=specs,fetch_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    with Path('research/evidence/autoresearch_exam_task_specs_v1.json').open('x',encoding='utf8') as f:
        json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'revision':REV,'files':len(files),'bytes':sum(v['bytes'] for v in files.values()),'tasks':len(specs)}))
    for row in specs:print(row['task'],json.dumps(row['spec'].get('environment',{})))


if __name__=='__main__':main()
