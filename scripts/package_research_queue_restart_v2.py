"""Preserve failed batches and restart with a placement-log-only VAKRA repair."""
import hashlib
import json
from pathlib import Path
import zipfile


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def main():
    specifications = [
        ('vakra-expansion-v1', 'vakra-expansion-v2', 'run_vakra_expansion_v1.py',
         'f76dae6430ca433afad53b39b1c54e67d777802d2f95dbcb1c81c674180fbc61'),
        ('vakra-output-budget-v1', 'vakra-output-budget-v2', 'run_vakra_output_budget_v1.py',
         'd86b61d89bd7cf0004311d27c8d0e0ae924eb48822ef5d29b687227404b90bd9'),
        ('tau-memory-test40-ties-code-v2', 'tau-memory-test40-ties-code-v3', 'run_memory_test40_ties_v1.py',
         'd7a23dbe7876d5bcc0d70738ef147c6b17908e39552d4ad7b6286980905f8b3a'),
        ('nk-prefix-curation-v1', 'nk-prefix-curation-v2', 'run_nk_prefix_curation_v1.py',
         'd14757ed8580f726ab8f33b16b1e95479b357d741c4d44fca9066fc6e0cfe2c9'),
        ('tau-nk-test40-v1', 'tau-nk-test40-v2', 'run_tau_nk_test40_v1.py',
         '0b02ab2ce1bf6582bd4040c2fe73cc1d05e127cfc714bc2caece6bbb0a95ad46'),
    ]
    replacements = {old: new for old, new, _, _ in specifications}
    replacements['tau-memory-test40-ties-v1'] = 'tau-memory-test40-ties-v2'
    combined, records = {}, []
    for old, new, script, expected in specifications:
        path = Path('results/deploy') / (old + '.zip')
        assert digest(path.read_bytes()) == expected
        with zipfile.ZipFile(path) as archive:
            contents = {n: archive.read(n) for n in archive.namelist()}
        original = dict(contents)
        # Retain every originally registered source and protocol. The new
        # supervisor is separately identified, with only batch/dependency paths changed.
        body = contents['scripts/' + script].decode('utf-8')
        for before, after in replacements.items():
            body = body.replace(before, after)
        contents['scripts/restart_registered_queue_v2.py'] = body.encode('utf-8')
        if old.startswith('vakra-'):
            name = 'autolab/vakra_native.py'
            contents[name] = Path(name).read_bytes()
            if old == 'vakra-output-budget-v1':
                name = 'autolab/vakra_budget_replay.py'
                contents[name] = Path(name).read_bytes()
        changed = {n: {'before': digest(original[n]), 'after': digest(b)}
                   for n, b in contents.items() if n in original and b != original[n]}
        assert set(changed) <= {'autolab/vakra_native.py', 'autolab/vakra_budget_replay.py'}
        record = dict(original_revision=old, revision=new, original_archive_sha256=expected,
                      batch=replacements.get('tau-memory-test40-ties-v1') if 'ties' in old else new,
                      changed_existing_files=changed,
                      supervisor_sha256=digest(contents['scripts/restart_registered_queue_v2.py']),
                      preserved_protocol_files={n:digest(b) for n,b in contents.items() if n.startswith('protocol/')})
        records.append(record)
        # Standalone revised archive supplies exact sources to the later analyzer.
        revised = Path('results/deploy') / (new + '.zip')
        with zipfile.ZipFile(revised, 'x', zipfile.ZIP_DEFLATED) as archive:
            for name, blob in sorted(contents.items()):
                archive.writestr(name, blob)
                combined[new + '/' + name] = blob
        record['archive_sha256'] = digest(revised.read_bytes())
    amendment = dict(
        purpose='Infrastructure restart before any affected task generation; preserve original failed artifacts.',
        reason='torch.device values in single-GPU hf_device_map could not be serialized to JSON.',
        scientific_changes='None: tasks, prompts, source choices, checkpoints, sampling, budgets and scoring masks retained.',
        fix='Convert only recorded device-map values to strings in VAKRA run and output-budget metadata; inference code unchanged.',
        supervisors='New explicitly hashed entrypoints change only run/revision/dependency path identifiers; original registered scripts remain preserved.',
        revisions=records)
    combined['restart_amendment.json'] = json.dumps(amendment, indent=2).encode('utf-8')
    manifest = {name:digest(blob) for name,blob in sorted(combined.items())}
    combined['bundle_manifest.json'] = json.dumps(manifest, indent=2).encode('utf-8')
    output = Path('results/deploy/research-queue-restart-v2.zip')
    with zipfile.ZipFile(output, 'x', zipfile.ZIP_DEFLATED) as archive:
        for name,blob in sorted(combined.items()):
            assert '..' not in Path(name).parts and not name.endswith(('.env', '.pyc'))
            archive.writestr(name,blob)
    amendment.update(bundle_sha256=digest(output.read_bytes()), bundle_bytes=output.stat().st_size,
                     bundle_members=len(combined))
    evidence = Path('research/evidence/research_queue_restart_amendment_v2.json')
    with evidence.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(amendment, stream, indent=2)
        stream.write('\n')
    print(json.dumps(amendment))


if __name__ == '__main__':
    main()
