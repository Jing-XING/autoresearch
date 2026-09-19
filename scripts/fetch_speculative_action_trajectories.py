"""Acquire the complete normal/simulated HotPotQA trace slice at a fixed commit."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import urllib.request

from scripts.fetch_speculative_action_sources import ROOT, REPO, COMMIT, TREE_SHA256


def main():
    tree_bytes = (ROOT/'tree.json').read_bytes()
    assert hashlib.sha256(tree_bytes).hexdigest() == TREE_SHA256
    tree = json.loads(tree_bytes)
    assert not tree['truncated']
    rows = sorted((r for r in tree['tree'] if r['type'] == 'blob'
                   and r['path'].startswith('hotpotqa/run_metrics/')
                   and Path(r['path']).name in {'normalobs.json', 'simobs.json'}), key=lambda r: r['path'])
    assert len(rows) == 188 and sum(r['size'] for r in rows) == 1771046
    def obtain(row):
        rel = row['path']
        assert not Path(rel).is_absolute() and '..' not in Path(rel).parts
        path = ROOT/'archive'/rel
        if path.exists():
            data = path.read_bytes()
        else:
            request = urllib.request.Request(f'https://raw.githubusercontent.com/{REPO}/{COMMIT}/{rel}',
                                             headers={'User-Agent': 'public-research-artifact-audit'})
            data = urllib.request.urlopen(request, timeout=45).read()
        assert len(data) == row['size']
        assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest() == row['sha'], rel
        json.loads(data)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as stream:
                stream.write(data)
        return rel, {'sha256': hashlib.sha256(data).hexdigest(), 'git_blob': row['sha'], 'bytes': len(data)}
    with ThreadPoolExecutor(max_workers=8) as pool:
        files = dict(pool.map(obtain, rows))
    result = {'repository': REPO, 'commit': COMMIT, 'tree_sha256': TREE_SHA256,
              'selection': 'all normalobs.json and simobs.json files below hotpotqa/run_metrics at the pinned commit',
              'files': files, 'bytes': sum(r['bytes'] for r in files.values())}
    out = Path('research/evidence/speculative_action_trajectory_manifest_v1.json')
    if out.exists():
        assert json.loads(out.read_bytes()) == result
    else:
        out.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({'files': len(files), 'bytes': result['bytes'], 'executed_upstream': False}))


if __name__ == '__main__':
    main()
