"""Bundle explicit Python sources and frozen registration, excluding private configuration."""
import hashlib
import json
from pathlib import Path
import zipfile


def main():
    contents = {p.as_posix(): p.read_bytes() for folder in ('autolab', 'tests')
                for p in sorted(Path(folder).glob('*.py'))}
    for filename in ('scripts/run_memory_test40_ties_v1.py', 'scripts/preflight_memory_tie_transfer.py',
                     'research/memory_test40_tie_protocol.md'):
        contents[filename] = Path(filename).read_bytes()
    registration = Path('research/evidence/memory_test40_tie_registration_v1.json').read_bytes()
    contents['protocol/registration.json'] = registration
    value = json.loads(registration)
    assert value['registered_episodes'] == 560 and value['target_outputs_seen'] is False
    for filename, digest in value['source_files_sha256'].items():
        assert hashlib.sha256(contents[filename]).hexdigest() == digest
    output = Path('results/deploy/tau-memory-test40-ties-code-v2.zip')
    with zipfile.ZipFile(output, 'x', zipfile.ZIP_DEFLATED) as z:
        for name, data in sorted(contents.items()):
            assert '..' not in Path(name).parts and name.endswith(('.py', '.md', '.json'))
            z.writestr(name, data)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    manifest = {'archive_sha256': digest,
                'files': {n: hashlib.sha256(b).hexdigest() for n, b in sorted(contents.items())}}
    Path('results/deploy/tau-memory-test40-ties-code-v2-manifest.json').write_text(json.dumps(manifest, indent=2))
    receipt = json.dumps({'archive_sha256': digest, 'files_verified': len(contents)}, sort_keys=True).encode()
    Path('results/deploy/tau-memory-test40-ties-code-v2-receipt-expected.json').write_bytes(receipt)
    print(json.dumps({'bytes': output.stat().st_size, 'members': len(contents), 'sha256': digest,
                      'receipt_sha256': hashlib.sha256(receipt).hexdigest()}))


if __name__ == '__main__':
    main()
