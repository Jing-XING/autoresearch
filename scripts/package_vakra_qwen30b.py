"""Package already prepared public tasks and explicit source files, excluding secrets."""
import hashlib
import json
from pathlib import Path
import zipfile


def main():
    base = Path('results/deploy/vakra-smollm3-v1.zip')
    assert hashlib.sha256(base.read_bytes()).hexdigest() == '267458daa67dc7bf5bc378214540c3194136f077380359bf82b22acf3b2357b6'
    with zipfile.ZipFile(base) as z:
        contents = {n: z.read(n) for n in z.namelist() if n.startswith(('autolab/', 'prepared/', 'upstream/', 'tests/'))}
    explicit = ['autolab/local_smoke.py', 'autolab/native_tool_agent.py', 'autolab/vakra_native.py',
                'tests/test_model_placement.py', 'scripts/run_vakra_qwen30b_v1.py',
                'scripts/qwen30b_infrastructure_smoke.py', 'research/evidence/qwen30b_capacity_control_protocol.md',
                'research/evidence/qwen30b_download_manifest.json']
    for name in explicit:
        contents[name] = Path(name).read_bytes()
    selection = json.loads(Path('research/evidence/vakra_crossdomain_setup_audit.json').read_bytes())
    selection.update(registered_episodes=120, template_profile='standard', device_profile='two_gpu_balanced',
                     model_revision='0d7cf23991f47feeb3a57ecb4c9cee8ea4a17bfe',
                     purpose='Known-task larger-model capacity follow-up, not independent task confirmation')
    for domain in selection['domains']:
        domain['registered_episodes'] = 40
    contents['protocol/selection.json'] = json.dumps(selection, indent=2).encode()
    out = Path('results/deploy/vakra-qwen30b-v1.zip')
    with zipfile.ZipFile(out, 'x', zipfile.ZIP_DEFLATED) as z:
        for name, data in sorted(contents.items()):
            assert not name.endswith(('.env', '.pyc')) and '..' not in Path(name).parts
            z.writestr(name, data)
    manifest = {'archive_sha256': hashlib.sha256(out.read_bytes()).hexdigest(),
                'files': {n: hashlib.sha256(b).hexdigest() for n, b in sorted(contents.items())}}
    Path('results/deploy/vakra-qwen30b-v1-manifest.json').write_text(json.dumps(manifest, indent=2))
    receipt = json.dumps({'archive_sha256': manifest['archive_sha256'], 'files_verified': len(contents)}, sort_keys=True).encode()
    Path('results/deploy/vakra-qwen30b-v1-receipt-expected.json').write_bytes(receipt)
    print(json.dumps({'bytes': out.stat().st_size, 'files': len(contents), 'archive_sha256': manifest['archive_sha256'],
                      'receipt_sha256': hashlib.sha256(receipt).hexdigest()}))


if __name__ == '__main__':
    main()
