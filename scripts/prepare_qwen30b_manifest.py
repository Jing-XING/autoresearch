"""Pin official public weights and tokenizer artifacts for a larger capacity control."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import urllib.request


def main():
    root = Path('results/models/qwen30b')
    metadata_path = root / 'official-metadata.json'
    raw = metadata_path.read_bytes()
    meta = json.loads(raw)
    assert meta['id'] == 'Qwen/Qwen3-30B-A3B-Instruct-2507'
    names = {'config.json', 'generation_config.json', 'merges.txt',
             'tokenizer.json', 'tokenizer_config.json', 'vocab.json',
             'model.safetensors.index.json'}
    selected = [r for r in meta['siblings'] if r['rfilename'] in names or r['rfilename'].endswith('.safetensors')]
    assert len(selected) == 23

    def pin(row):
        name = row['rfilename']
        if row.get('lfs'):
            digest = row['lfs']['sha256']
        else:
            url = f"https://huggingface.co/{meta['id']}/resolve/{meta['sha']}/{name}"
            data = urllib.request.urlopen(url, timeout=60).read()
            assert len(data) == row['size']
            git_blob = b'blob ' + str(len(data)).encode() + b'\0' + data
            assert hashlib.sha1(git_blob).hexdigest() == row['blobId']
            digest = hashlib.sha256(data).hexdigest()
            target = root / name
            if target.exists():
                assert target.read_bytes() == data
            else:
                target.write_bytes(data)
        return {'name': name, 'bytes': row['size'], 'sha256': digest}

    with ThreadPoolExecutor(max_workers=4) as pool:
        files = sorted(pool.map(pin, selected), key=lambda r: r['name'])
    manifest = {'model_id': meta['id'], 'revision': meta['sha'], 'license': meta['cardData']['license'],
                'official_metadata_sha256': hashlib.sha256(raw).hexdigest(),
                'mirror': 'https://modelscope.cn/models/Qwen/Qwen3-30B-A3B-Instruct-2507/resolve/master/',
                'files': files,
                'verification': 'Official immutable HF revision; small Git blobs verified against blobId, large files pinned by official LFS SHA256. Mutable mirror accepted only on exact length and SHA256 equality. No config_1m override.'}
    output = Path('research/evidence/qwen30b_download_manifest.json')
    with output.open('x', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
    print(json.dumps({'revision': meta['sha'], 'files': len(files), 'bytes': sum(r['bytes'] for r in files)}))


if __name__ == '__main__':
    main()
