"""Acquire the complete pinned official harness for inspection, without imports."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import urllib.request

REPO = 'bespokelabsai/AutoResearchExam-Terminus'
REV = 'a2a8381236a21092a05022f3aa71fd59d508ae39'
TREE_SHA = '5d588ffe9f036fd75e8c665dfa273fcf5904a3a251bf83be2f4241d7cfa17481'
ROOT = Path('results/third_party/autoresearch-exam-terminus')


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'research-artifact-audit'}), timeout=45).read()


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    tp = ROOT/'tree.json'
    if not tp.exists():
        blob = get(f'https://api.github.com/repos/{REPO}/git/trees/{REV}?recursive=1')
        assert hashlib.sha256(blob).hexdigest() == TREE_SHA
        tp.write_bytes(blob)
    assert hashlib.sha256(tp.read_bytes()).hexdigest() == TREE_SHA
    tree = json.loads(tp.read_bytes())
    assert not tree['truncated']
    entries = [r for r in tree['tree'] if r['type'] == 'blob']
    def fetch(row):
        rel = row['path']
        assert not Path(rel).is_absolute() and '..' not in Path(rel).parts
        target = ROOT/'source'/rel
        blob = target.read_bytes() if target.exists() else get(f'https://raw.githubusercontent.com/{REPO}/{REV}/{rel}')
        assert len(blob) == row['size']
        assert hashlib.sha1(b'blob '+str(len(blob)).encode()+b'\0'+blob).hexdigest() == row['sha']
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as f:
                f.write(blob)
        return rel, {'sha256': hashlib.sha256(blob).hexdigest(), 'git_blob': row['sha'], 'bytes': len(blob)}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        files = dict(pool.map(fetch, entries))
    manifest = {'repository': REPO, 'revision': REV, 'tree_sha256': TREE_SHA,
                'scope': 'all tracked blobs; no upstream imports, model calls or task test-data access',
                'files': files}
    output = Path('research/evidence/autoresearch_exam_harness_source_v1.json')
    if output.exists():
        assert json.loads(output.read_bytes()) == manifest
    else:
        with output.open('x', encoding='utf-8', newline='\n') as f:
            json.dump(manifest, f, indent=2)
            f.write('\n')
    print(json.dumps({'files': len(files), 'bytes': sum(r['bytes'] for r in files.values()), 'revision': REV}))


if __name__ == '__main__':
    main()
