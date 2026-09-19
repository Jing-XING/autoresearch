"""Archive the executed native-airline controls and all retained attempts."""
import hashlib
import json
from pathlib import Path
import zipfile


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    report_path = Path('research/evidence/tau_airline_compensation_probe_v1.json')
    report = json.loads(report_path.read_bytes())
    files = set()
    for directory in [report['raw_directory'], report['initial_attempt']['raw_directory'], report['second_attempt']['raw_directory']]:
        root = Path(directory).resolve()
        assert root.is_relative_to(Path('results/probes/tau-airline-mcp').resolve())
        files.update(p for p in root.iterdir() if p.is_file() and p.suffix in ('.json', '.jsonl'))
    files.update(Path(p).resolve() for p in report['scripts_sha256'])
    files.update(Path(p).resolve() for p in [
        report['initial_attempt']['script_snapshot'], report['second_attempt']['script_snapshot'],
        str(report_path), 'research/evidence/tau_airline_compensation_preflight_v1.json',
        'research/evidence/tau_airline_compensation_validation_v1.json',
        'research/evidence/tau2_source_manifest.json', 'scripts/validate_tau_airline_compensation.py',
        'scripts/package_tau_airline_compensation.py',
        'results/reviews/tau_airline_child_runtime_v1.json', 'results/reviews/tau_native_mcp_install_v1.json',
        'results/reviews/tau_airline_fixture_source_receipt_v1.json',
        'results/third_party/tau2-airline-fixture/test_tools_airline.py',
        'results/third_party/tau2-bench/LICENSE'])
    for attempt in (1, 2, 3):
        files.update(Path(f'results/reviews/tau_airline_compensation_probe_v{attempt}.{suffix}.log').resolve()
                     for suffix in ('stdout', 'stderr'))
    root = Path.cwd().resolve()
    manifest = {p.relative_to(root).as_posix(): sha(p) for p in sorted(files)}
    assert not any(Path(p).name == '.env' for p in manifest)
    output = Path('results/remote/tau-airline-compensation-v1-evidence.zip')
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for rel in manifest:
            z.write(root/rel, rel)
        z.writestr('artifact_manifest.json', json.dumps(manifest, indent=2)+'\n')
    with zipfile.ZipFile(output) as z:
        assert z.testzip() is None
        for rel, digest in manifest.items():
            assert hashlib.sha256(z.read(rel)).hexdigest() == digest
    receipt = {'file': str(output), 'bytes': output.stat().st_size, 'sha256': sha(output),
               'entries': len(manifest)+1, 'files': manifest, 'validated_cases': 25,
               'scope': 'all final native airline controls, source fixture, runtime inventory, and retained partial attempts'}
    Path('research/evidence/tau_airline_compensation_raw_receipt_v1.json').write_text(
        json.dumps(receipt, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ['file', 'bytes', 'sha256', 'entries']}))


if __name__ == '__main__':
    main()
