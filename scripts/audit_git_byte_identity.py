"""Compare tracked experimental JSON/Python bytes with an index or commit tree."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tree', default='HEAD', help='Commit-ish, or INDEX for staged blobs')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    names = subprocess.check_output(['git','ls-files','-z','--','*.py','*.json','*.jsonl']).decode().split('\0')
    names = [name for name in names if name and name != args.output.as_posix()]
    prefix = ':' if args.tree == 'INDEX' else args.tree + ':'
    payload = ''.join(prefix + name + '\n' for name in names).encode()
    process = subprocess.run(['git','cat-file','--batch'], input=payload, capture_output=True, check=True)
    data, offset, rows = process.stdout, 0, []
    for name in names:
        end = data.index(b'\n', offset)
        header = data[offset:end].decode()
        parts = header.split()
        if len(parts) != 3 or parts[1] != 'blob':
            raise ValueError('Missing blob in requested tree: ' + name)
        size = int(parts[2]);start = end+1
        saved = data[start:start+size]
        assert data[start+size:start+size+1] == b'\n'
        offset = start+size+1
        local = Path(name).read_bytes()
        if local != saved:
            rows.append(dict(path=name, local_sha256=hashlib.sha256(local).hexdigest(),
                tree_sha256=hashlib.sha256(saved).hexdigest(),
                only_crlf_normalization=local.replace(b'\r\n',b'\n') == saved.replace(b'\r\n',b'\n')))
    assert offset == len(data)
    result = dict(purpose=__doc__, tree=args.tree, tracked_files_checked=len(names),
        mismatched_files=len(rows), mismatches=rows,
        scope='Tracked JSON, JSONL and Python files only; ignored remote artifacts are not part of this check.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps({k:result[k] for k in ('tree','tracked_files_checked','mismatched_files')}))


if __name__ == '__main__':
    main()
