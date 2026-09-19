"""Download the registered three-domain replication, without executing code."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.error
import urllib.request

REV='1388b9f1aaed887a73957eba651a6c2034010476'
BASE=Path('results/third_party')
DATA=BASE/'vakra-data'


def main():
    meta=json.loads((BASE/'vakra_hf_metadata.json').read_bytes())
    assert meta['sha']==REV
    tree=json.loads((BASE/'vakra_database_tree.json').read_bytes())
    available={x['rfilename'] for x in meta['siblings']}
    domains={Path(p).stem for p in available if p.startswith('train/capability_1_bi_apis/input/') and p.endswith('.json')}
    dbs=sorted([x for x in tree if x['path'].endswith('.sqlite') and Path(x['path']).stem in domains-{'world'}],key=lambda x:(x['size'],x['path']))[:3]
    assert [Path(x['path']).stem for x in dbs]==['computer_student','cars','book_publishing_company']
    files=[]
    for db in dbs:
        d=Path(db['path']).stem
        for path in (f'train/capability_1_bi_apis/input/{d}.json',f'train/capability_1_bi_apis/output/{d}.json',db['path']):
            assert path in available
            files.append((path,db if path==db['path'] else None))
    def download(item):
        path,db=item
        destination=DATA/path
        # Git blobs can use raw; LFS pointers require resolved content.
        route='resolve' if db and 'lfs' in db else 'raw'
        url=f'https://huggingface.co/datasets/ibm-research/VAKRA/{route}/{REV}/{path}'
        if route=='resolve':url+='?download=true'
        try:
            with urllib.request.urlopen(url,timeout=45) as response:
                content=response.read(5_000_001)
        except urllib.error.URLError:
            # OS curl uses a different TLS stack; no certificate bypass.
            result=subprocess.run(['curl.exe','--silent','--show-error','--fail',
                '--location','--max-time','45',url],capture_output=True,timeout=50)
            if result.returncode:
                raise RuntimeError(path+': '+result.stderr.decode(errors='replace')[:300])
            content=result.stdout
        if len(content)>5_000_000:
            raise ValueError('Unexpected file size')
        if db:
            assert len(content)==db['size']
            if 'lfs' in db:
                assert hashlib.sha256(content).hexdigest()==db['lfs']['oid']
            else:
                blob=b'blob '+str(len(content)).encode()+b'\0'+content
                assert hashlib.sha1(blob).hexdigest()==db['oid']
        else:
            assert isinstance(json.loads(content),list)
        destination.parent.mkdir(parents=True,exist_ok=True)
        if destination.exists():
            assert destination.read_bytes()==content,'Previously downloaded content differs'
        else:
            with destination.open('xb') as f:f.write(content)
        return {'path':path,'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest()}
    with ThreadPoolExecutor(max_workers=3) as pool:
        records=list(pool.map(download,files))
    manifest={'revision':REV,'selection':'three smallest non-world capability-1 SQLite files, size then path',
              'database_tree_sha256':hashlib.sha256((BASE/'vakra_database_tree.json').read_bytes()).hexdigest(),
              'selected_database_metadata':dbs,'files':records,
              'task_counts':{Path(d['path']).stem:len(json.loads((DATA/f"train/capability_1_bi_apis/input/{Path(d['path']).stem}.json").read_bytes())) for d in dbs}}
    with (DATA/'replication-download-manifest.json').open('x',encoding='utf-8') as f:json.dump(manifest,f,indent=2)
    print(json.dumps({'files':len(records),'task_counts':manifest['task_counts']}))


if __name__=='__main__':
    main()
