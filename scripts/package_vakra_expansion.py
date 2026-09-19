"""Package fresh public domains and the fixed runner, keeping SQL cards offline."""
import hashlib
import json
from pathlib import Path
import zipfile


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    base = Path('results/deploy/vakra-qwen30b-v1.zip')
    assert sha(base) == '9d4bfabd959a02a0c72aca3fc054d7f028aa34403bcbbef391ecd147080b9d1f'
    with zipfile.ZipFile(base) as z:
        contents = {n: z.read(n) for n in z.namelist() if n.startswith(('autolab/', 'tests/', 'upstream/'))}
    for name in ('scripts/run_vakra_expansion_v1.py',):
        contents[name] = Path(name).read_bytes()
    setup_path = Path('research/evidence/vakra_domain_expansion_setup_v1.json')
    setup = json.loads(setup_path.read_bytes())
    cards_path = Path('research/evidence/vakra_domain_expansion_sql_cards_v1.json')
    cards = json.loads(cards_path.read_bytes())
    assert cards['model_answers_seen'] is False and cards['setup_sha256'] == sha(setup_path)
    registration_path = Path('research/evidence/vakra_domain_expansion_registration_v1.json')
    selection = {'registered_episodes': 420, 'setup_sha256': sha(setup_path),
                 'offline_sql_cards_sha256': sha(cards_path), 'registration_sha256': sha(registration_path),
                 'prompts': ['original', 'coverage_check'], 'models': ['qwen3', 'qwen25', 'qwen30b'],
                 'call_policy': 'sequential', 'domains': []}
    for domain in setup['domains']:
        name = domain['domain']
        prepared = Path('results/vakra-domain-expansion-v1') / name
        manifest = json.loads((prepared / 'preparation_manifest.json').read_bytes())
        assert sha(prepared / 'preparation_manifest.json') == domain['preparation_sha256']
        assert sha(prepared / (name + '.sqlite')) == domain['database_sha256']
        for rel, digest in manifest['runtime_files'].items():
            p = prepared / 'runtime' / rel
            assert sha(p) == digest
            contents[f'prepared/{name}/runtime/{rel}'] = p.read_bytes()
        for rel in ('queries.json', name + '.sqlite', 'preparation_manifest.json'):
            contents[f'prepared/{name}/{rel}'] = (prepared / rel).read_bytes()
        selection['domains'].append({k: domain[k] for k in ('domain', 'available_queries', 'selected_task_ids',
                                                            'preparation_sha256', 'database_sha256', 'registered_episodes')})
    contents['protocol/selection.json'] = json.dumps(selection, indent=2).encode()
    out = Path('results/deploy/vakra-expansion-v1.zip')
    with zipfile.ZipFile(out, 'x', zipfile.ZIP_DEFLATED) as z:
        for name, data in sorted(contents.items()):
            assert '..' not in Path(name).parts and not name.endswith(('.env', '.pyc'))
            assert 'sql_cards' not in name and '/output/' not in name
            z.writestr(name, data)
    manifest = {'archive_sha256': sha(out), 'files': {n: hashlib.sha256(b).hexdigest() for n,b in sorted(contents.items())}}
    Path('results/deploy/vakra-expansion-v1-manifest.json').write_text(json.dumps(manifest, indent=2))
    receipt = json.dumps({'archive_sha256': sha(out), 'files_verified': len(contents)}, sort_keys=True).encode()
    Path('results/deploy/vakra-expansion-v1-receipt-expected.json').write_bytes(receipt)
    print(json.dumps({'archive_bytes':out.stat().st_size, 'members':len(contents), 'sha256':sha(out),
                      'receipt_sha256':hashlib.sha256(receipt).hexdigest()}))


if __name__ == '__main__':
    main()
