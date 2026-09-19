"""Build a bounded public-data/own-code package; never include hidden task files."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    files = [
        'autolab/__init__.py', 'autolab/runner.py', 'autolab/risk_development.py',
        'scripts/run_risk_development_controls.py', 'tests/test_risk_development.py',
        'research/risk_development_controls_v1.md',
        'research/evidence/autoresearch_exam_public_assets_v1.json',
    ]
    prefix = 'results/third_party/autoresearch-exam-tasks/source/'
    source = json.loads((ROOT / files[-1]).read_bytes())
    files += [prefix + p for p in source['files']
              if p.startswith('label-efficient-risk-estimator/environment/app/data/dev/')]
    files += [prefix + 'LICENSE', prefix + 'label-efficient-risk-estimator/instruction.md']
    contents = {rel: (ROOT / rel).read_bytes() for rel in files}
    manifest = dict(purpose='Trusted public-development risk baselines, no private grader or model.',
                    files={rel: dict(bytes=len(b), sha256=hashlib.sha256(b).hexdigest())
                           for rel, b in contents.items()})
    archive = ROOT / 'results/deploy/risk-development-controls-v1.zip'
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as z:
        for rel, b in contents.items(): z.writestr(rel, b)
        z.writestr('deployment_manifest.json', json.dumps(manifest, indent=2) + '\n')
    receipt = dict(archive=archive.relative_to(ROOT).as_posix(), bytes=archive.stat().st_size,
                   sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                   payload_files=len(contents), entries=len(contents)+1, manifest=manifest)
    out = ROOT / 'research/evidence/risk_development_controls_package_v1.json'
    with out.open('x', encoding='utf8') as f:
        json.dump(receipt, f, indent=2); f.write('\n')
    print(json.dumps({k: v for k, v in receipt.items() if k != 'manifest'}))


if __name__ == '__main__': main()
