"""Download an explicit public safetensors manifest, verifying every file.

Incomplete attempts remain under .part names; no existing directory is reused.
No downloaded Python or pickle is executed by this script.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import time
import urllib.request


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    raw = a.manifest.read_bytes()
    manifest = json.loads(raw)
    assert manifest['mirror'].startswith('https://modelscope.cn/models/')
    assert all(Path(r['name']).name == r['name'] and '/' not in r['name'] and '\\' not in r['name']
               and (r['name'].endswith(('.json', '.jinja', '.safetensors')) or r['name'] == 'merges.txt')
               for r in manifest['files'])
    assert shutil.disk_usage(a.output.parent).free > 2.2 * sum(r['bytes'] for r in manifest['files'])
    a.output.mkdir(exist_ok=False)
    report = {'status': 'running', 'started': time.time(), 'model_id': manifest['model_id'],
              'revision': manifest['revision'], 'manifest_sha256': hashlib.sha256(raw).hexdigest(),
              'files': [], 'attempts': []}
    status = a.output / 'download_status.json'
    deadline = time.monotonic() + 3600

    def save():
        status.write_text(json.dumps(report, indent=2), encoding='utf-8')

    save()
    try:
        for entry in manifest['files']:
            target = a.output / entry['name']
            for attempt in range(2):
                part = a.output / (entry['name'] + f'.attempt-{attempt}.part')
                trace = {'file': entry['name'], 'attempt': attempt, 'started': time.time()}
                report['attempts'].append(trace)
                try:
                    request = urllib.request.Request(manifest['mirror'] + entry['name'],
                                                     headers={'User-Agent': 'autoresearch-research/1.0'})
                    digest = hashlib.sha256()
                    count = 0
                    with urllib.request.urlopen(request, timeout=60) as response, part.open('xb') as f:
                        while True:
                            if time.monotonic() > deadline:
                                raise TimeoutError('Registered one-hour download limit')
                            chunk = response.read(4 * 1024 * 1024)
                            if not chunk:
                                break
                            count += len(chunk)
                            if count > entry['bytes']:
                                raise ValueError('Response exceeds pinned size')
                            digest.update(chunk)
                            f.write(chunk)
                    assert count == entry['bytes'], 'Pinned size mismatch'
                    assert digest.hexdigest() == entry['sha256'], 'Pinned SHA256 mismatch'
                    assert not target.exists() and target.resolve().parent == a.output.resolve()
                    assert part.resolve().parent == a.output.resolve()
                    part.rename(target)
                    trace.update(status='verified', finished=time.time())
                    report['files'].append(entry)
                    save()
                    print(json.dumps({'verified': entry['name'], 'bytes': count}), flush=True)
                    break
                except Exception as exc:
                    trace.update(status='failed', error_type=type(exc).__name__, error=str(exc), finished=time.time())
                    save()
                    if attempt == 1 or time.monotonic() > deadline:
                        raise
        report['status'] = 'complete'
    except Exception as exc:
        report.update(status='failed', error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        report['finished'] = time.time()
        save()
        print(json.dumps({'status': report['status'], 'verified_files': len(report['files'])}), flush=True)


if __name__ == '__main__':
    main()
