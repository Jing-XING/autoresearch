"""Restore or verify only the public source files pinned by the executed study."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch-missing', action='store_true')
    args = parser.parse_args()
    evidence = json.loads(Path('research/evidence/independent_compensation_probe_v2.json').read_bytes())
    names = {'genglongling/SagaLLM':'sagallm', 'thomasjgeorge23/agent-saga':'agent-saga'}
    def obtain(path, url, expected):
        if not path.exists():
            if not args.fetch_missing:
                raise FileNotFoundError(path)
            request = urllib.request.Request(url, headers={'User-Agent':'public-research-source-reproduction'})
            blob = urllib.request.urlopen(request, timeout=45).read()
            assert hashlib.sha256(blob).hexdigest() == expected, url
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as stream:
                stream.write(blob)
        blob = path.read_bytes()
        assert hashlib.sha256(blob).hexdigest() == expected, str(path)
        return blob
    for manifest in evidence['source_manifests']:
        repo, revision = manifest['repository'], manifest['commit']
        root = Path('results/third_party') / names[repo]
        tree = json.loads(obtain(root/'tree.json',
            f'https://api.github.com/repos/{repo}/git/trees/{revision}?recursive=1', manifest['tree_sha256']))
        assert not tree['truncated']
        blobs = {r['path']:r['sha'] for r in tree['tree'] if r['type']=='blob'}
        for rel, expected in manifest['files'].items():
            assert not Path(rel).is_absolute() and '..' not in Path(rel).parts
            data = obtain(root/'source'/rel, f'https://raw.githubusercontent.com/{repo}/{revision}/{rel}', expected)
            assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest() == blobs[rel]
        path = root/'source_manifest.json'
        if not path.exists():
            path.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
        assert json.loads(path.read_bytes()) == manifest
        print(json.dumps({'repository':repo,'revision':revision,'verified_files':len(manifest['files'])}))


if __name__ == '__main__':
    main()
