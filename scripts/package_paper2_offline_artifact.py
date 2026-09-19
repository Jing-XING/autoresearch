"""Package explicit P2 research inputs; never walk private configuration roots."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
MODEL_ARCHIVES = [
    ('initial', 'vakra-native-first4-v1', 'vakra-native-first4-v1', 8),
    ('development', 'vakra-coverage12-v1', 'vakra-coverage12-v1', 48),
    ('strict', 'vakra-crossdomain-v1', 'vakra-crossdomain-v1', 240),
    ('sequential', 'vakra-permissive-v1', 'vakra-permissive-v1', 240),
    ('smollm3', 'vakra-smollm3-v1', 'vakra-smollm3-v1', 240),
    ('capacity', 'vakra-qwen30b-v1-complete', 'vakra-qwen30b-v1', 120),
    ('expansion', 'vakra-expansion-v2-complete', 'vakra-expansion-v2', 420),
    ('budget', 'vakra-output-budget-v2-complete', 'vakra-output-budget-v2', 12),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    paths = set()
    def add(path):
        p = (ROOT/path).resolve()
        assert p.is_file() and p.is_relative_to(ROOT)
        assert not any(x.lower() in ('.git', '.env', '__pycache__') for x in p.parts)
        paths.add(p)
    def tree(folder, suffixes):
        for p in (ROOT/folder).rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts and '.git' not in p.parts:
                if p.suffix.lower() in suffixes or p.name.startswith(('LICENSE', 'NOTICE')):
                    add(p)
    tree('autolab', {'.py'})
    tree('research/paper2', {'.md', '.bib', '.json', '.png', '.pdf', '.svg'})
    for p in (ROOT/'scripts').glob('*.py'):
        if 'vakra' in p.name or 'expansion_complete' in p.name or 'paper2' in p.name or p.name == 'build_review_pdf.py':
            add(p)
    for p in (ROOT/'tests').glob('*.py'):
        if 'vakra' in p.name or p.name in ('test_exact_paired_bootstrap.py', 'test_budget_complete_names.py', 'test_preview_cursor.py'):
            add(p)
    tracked = subprocess.check_output(['git', 'ls-files', 'research/evidence'], cwd=ROOT, text=True).splitlines()
    for name in tracked:
        p = Path(name)
        if 'vakra' in p.name or p.name in ('qwen30b_download_manifest.json', 'smollm3_download_manifest.json', 'paper2_review_pdf_v1.json'):
            add(p)
    for name in ('vakra-world-runtime-v3', 'vakra-computer_student-replication-v1',
                 'vakra-cars-replication-v1', 'vakra-book_publishing_company-replication-v1',
                 'vakra-domain-expansion-v1'):
        tree('results/'+name, {'.py', '.json', '.sqlite', '.md', '.txt', '.log'})
    tree('results/third_party/vakra', {'.py', '.md', '.txt', '.toml', '.yaml', '.yml'})
    add('results/third_party/vakra-data/README.md')
    for _, name, _, _ in MODEL_ARCHIVES:
        add('results/remote/'+name+'.zip')
    add('results/remote/vakra-cookbook-acquisition-v1-evidence.zip')
    for name in ('vakra-native-v3', 'vakra-crossdomain-v1', 'vakra-permissive-v1',
                 'vakra-smollm3-v1', 'vakra-qwen30b-v1', 'vakra-expansion-v2', 'vakra-output-budget-v2'):
        add('results/deploy/'+name+'.zip')
    add('output/pdf/paper2-scope-coverage-review.pdf')
    secret = re.compile(rb'(?:hf_[A-Za-z0-9]{25,}|sk-[A-Za-z0-9_-]{32,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)')
    files = []
    for p in sorted(paths):
        blob = p.read_bytes()
        assert not secret.search(blob), 'Credential-shaped content; inspect locally before packaging'
        if p.suffix == '.zip':
            with ZipFile(p) as z:
                for info in z.infolist():
                    assert '.env' not in Path(info.filename).parts and not secret.search(z.read(info)), 'Nested sensitive member'
        files.append({'path': p.relative_to(ROOT).as_posix(), 'bytes': len(blob),
                      'sha256': hashlib.sha256(blob).hexdigest()})
    manifest = {'format': 'paper2-offline-v1', 'source_commit': subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'source_note': 'Manifest hashes define included working-tree bytes, including the packaging/reanalysis additions.',
        'files': files, 'model_archives': [dict(key=k, path='results/remote/'+n+'.zip', batch=b, episodes=c)
                                       for k,n,b,c in MODEL_ARCHIVES],
        'scope': 'Saved-record reanalysis, not new inference or native MCP replay',
        'readme': 'research/paper2/artifact_README.md'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(args.output, 'x', ZIP_DEFLATED, compresslevel=6) as z:
        for r in files:
            z.writestr(r['path'], (ROOT/r['path']).read_bytes())
        z.writestr('paper2-artifact-manifest.json', json.dumps(manifest, indent=2)+'\n')
    print(json.dumps({'archive': str(args.output), 'bytes': args.output.stat().st_size,
                      'payload_files': len(files), 'model_records': 1328,
                      'sha256': hashlib.sha256(args.output.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
