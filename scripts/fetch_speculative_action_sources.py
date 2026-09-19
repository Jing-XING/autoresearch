"""Fetch a small, commit-pinned code-audit slice; never import upstream code."""
import hashlib
import json
from pathlib import Path
import urllib.request


ROOT = Path('results/third_party/speculative-action')
REPO = 'naimengye/speculative-action'
COMMIT = 'dc938b9ef7474caf07fe4ad16549c1fa8c7d268c'
TREE_SHA256 = 'd5e7f73c09500a5cc09eebf8abb50221f3c023ceab9f4eb0ccb7ef74bdf9fa95'
PATHS = [
    'README.md', 'e-commerce/README.md', 'e-commerce/tau-bench/README.md',
    'e-commerce/tau-bench/tau_bench/agents/tool_calling_agent.py',
    'e-commerce/tau-bench/tau_bench/agents/tool_calling_agent_reduce.py',
    'e-commerce/tau-bench/tau_bench/agents/tool_calling_agent_static.py',
    'e-commerce/tau-bench/tau_bench/run.py',
    'hotpotqa/README.md', 'hotpotqa/run.py',
    *['hotpotqa/src/' + n + '.py' for n in
      ['constants', 'environment', 'llm_client', 'metrics', 'prompts', 'runner', 'utils', 'wrappers']],
]


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    tree_path = ROOT/'tree.json'
    if not tree_path.exists():
        request = urllib.request.Request(
            f'https://api.github.com/repos/{REPO}/git/trees/{COMMIT}?recursive=1',
            headers={'User-Agent': 'public-research-source-audit'})
        tree_data = urllib.request.urlopen(request, timeout=45).read()
        assert hashlib.sha256(tree_data).hexdigest() == TREE_SHA256
        tree_path.write_bytes(tree_data)
    tree_data = tree_path.read_bytes()
    assert hashlib.sha256(tree_data).hexdigest() == TREE_SHA256
    tree = json.loads(tree_data)
    assert not tree['truncated']
    blobs = {r['path']: r['sha'] for r in tree['tree'] if r['type'] == 'blob'}
    files = {}
    for rel in PATHS:
        target = ROOT/'source'/rel
        if target.exists():
            data = target.read_bytes()
        else:
            request = urllib.request.Request(
                f'https://raw.githubusercontent.com/{REPO}/{COMMIT}/{rel}',
                headers={'User-Agent': 'public-research-source-audit'})
            data = urllib.request.urlopen(request, timeout=45).read()
        assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest() == blobs[rel], rel
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:
                stream.write(data)
        files[rel] = {'sha256': hashlib.sha256(data).hexdigest(), 'git_blob': blobs[rel], 'bytes': len(data)}
    manifest = {'repository': REPO, 'commit': COMMIT, 'tree_sha256': TREE_SHA256,
                'scope': 'static code audit acquisition, no upstream imports or experiments', 'files': files}
    out = Path('research/evidence/speculative_action_source_manifest_v1.json')
    if out.exists():
        assert json.loads(out.read_bytes()) == manifest
    else:
        out.write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({'verified_files': len(files), 'bytes': sum(r['bytes'] for r in files.values()), 'executed_upstream': False}))


if __name__ == '__main__':
    main()
