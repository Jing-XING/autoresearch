"""Freeze a prospective domain expansion using metadata, then retrieve public data."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'results/third_party'
REV = '1388b9f1aaed887a73957eba651a6c2034010476'
SEED = 'domain-expansion-20260919:'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    metadata = BASE / 'vakra_hf_metadata.json'
    tree_path = BASE / 'vakra_database_tree.json'
    meta, tree = [json.loads(p.read_bytes()) for p in (metadata, tree_path)]
    assert meta['sha'] == REV
    names = {x['rfilename'] for x in meta['siblings']}
    domains = {Path(p).stem for p in names if p.startswith('train/capability_1_bi_apis/input/') and p.endswith('.json')}
    eligible = [x for x in tree if x['path'].endswith('.sqlite') and x['size'] <= 5_000_000
                and Path(x['path']).stem in domains - {'computer_student', 'cars', 'book_publishing_company', 'world'}]
    ranked = sorted(eligible, key=lambda x: hashlib.sha256((SEED + Path(x['path']).stem).encode()).hexdigest())
    selected = ranked[:4]
    assert [Path(x['path']).stem for x in selected] == ['cookbook', 'disney', 'genes', 'ice_hockey_draft']
    registration = {'purpose': __doc__, 'dataset_revision': REV,
                    'metadata_sha256': sha(metadata), 'database_tree_sha256': sha(tree_path),
                    'selection': 'Exclude all four previously used domains; SQLite size <= 5000000 bytes; rank by SHA256 of seed plus domain; first four. No answer-dependent replacement.',
                    'seed': SEED, 'eligible_ranked': ranked, 'selected_databases': selected,
                    'task_selection': 'Within each domain, rank all UUIDs by SHA256 of task-expansion-20260919: plus UUID and retain the first min(20, available). Preserve deterministic rank order in execution.',
                    'evaluation': 'Fresh domains relative to this development work, still public training split; not guaranteed absent from model pretraining. Freeze SQL interpretations before model outputs. Retain interpretation ambiguities and execution failures.',
                    'models': ['qwen3', 'qwen25', 'qwen30b'], 'prompts': ['original', 'coverage_check'],
                    'executor': 'sequential', 'max_steps': 20, 'max_tool_calls': 20,
                    'max_new_tokens': 512, 'max_input_tokens': 32768,
                    'registration_stage': 'Before downloading task contents or observing model answers'}
    rp = ROOT / 'research/evidence/vakra_domain_expansion_registration_v1.json'
    if rp.exists():
        assert json.loads(rp.read_bytes()) == registration
    else:
        with rp.open('x', encoding='utf-8') as f:
            json.dump(registration, f, indent=2)
    files = []
    for db in selected:
        domain = Path(db['path']).stem
        for path in (f'train/capability_1_bi_apis/input/{domain}.json',
                     f'train/capability_1_bi_apis/output/{domain}.json', db['path']):
            assert path in names
            files.append((path, db if path == db['path'] else None))

    def retrieve(item):
        path, db = item
        route = 'resolve' if db and 'lfs' in db else 'raw'
        url = f'https://huggingface.co/datasets/ibm-research/VAKRA/{route}/{REV}/{path}'
        if route == 'resolve':
            url += '?download=true'
        p = subprocess.run(['curl.exe', '--silent', '--show-error', '--fail', '--location',
                            '--max-time', '60', url], capture_output=True, timeout=70)
        if p.returncode:
            raise RuntimeError(path + ': ' + p.stderr.decode(errors='replace')[:300])
        content = p.stdout
        assert len(content) <= 20_000_000
        if db:
            assert len(content) == db['size']
            if 'lfs' in db:
                assert hashlib.sha256(content).hexdigest() == db['lfs']['oid']
            else:
                assert hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest() == db['oid']
        else:
            assert isinstance(json.loads(content), list)
        out = BASE / 'vakra-data' / path
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists():
            assert out.read_bytes() == content
        else:
            with out.open('xb') as f:
                f.write(content)
        return {'path': path, 'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()}

    with ThreadPoolExecutor(max_workers=3) as executor:
        records = list(executor.map(retrieve, files))
    selections = []
    for db in selected:
        domain = Path(db['path']).stem
        tasks = json.loads((BASE / f'vakra-data/train/capability_1_bi_apis/input/{domain}.json').read_bytes())
        ids = [q['uuid'] for q in tasks]
        assert len(set(ids)) == len(ids)
        ids.sort(key=lambda uid: hashlib.sha256(('task-expansion-20260919:' + uid).encode()).hexdigest())
        selections.append({'domain': domain, 'available': len(ids), 'selected_uuids': ids[:20]})
    result = {'registration_sha256': sha(rp), 'files': records, 'selection': selections,
              'registered_model_episodes': sum(len(x['selected_uuids']) for x in selections) * 6}
    with (ROOT / 'research/evidence/vakra_domain_expansion_download_v1.json').open('x', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    print(json.dumps({'domains': [r['domain'] for r in selections],
                      'task_counts': [len(r['selected_uuids']) for r in selections],
                      'registered_model_episodes': result['registered_model_episodes']}))


if __name__ == '__main__':
    main()
