"""Add the checked-input budget replay to the immutable domain-expansion bundle."""
import hashlib
import json
from pathlib import Path
import zipfile


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    base=Path('results/deploy/vakra-expansion-v1.zip')
    assert sha(base)=='f76dae6430ca433afad53b39b1c54e67d777802d2f95dbcb1c81c674180fbc61'
    with zipfile.ZipFile(base) as z:
        contents={n:z.read(n) for n in z.namelist() if n.startswith(('autolab/','tests/','prepared/','upstream/'))}
    for name in ('autolab/vakra_budget_replay.py','tests/test_budget_replay_guard.py',
                 'scripts/run_vakra_output_budget_v1.py','research/evidence/vakra_expansion_length_sensitivity_registration_v1.md'):
        contents[name]=Path(name).read_bytes()
    out=Path('results/deploy/vakra-output-budget-v1.zip')
    with zipfile.ZipFile(out,'x',zipfile.ZIP_DEFLATED) as z:
        for name,data in sorted(contents.items()):
            assert '..' not in Path(name).parts and not name.endswith(('.env','.pyc'))
            assert 'sql_cards' not in name and '/output/' not in name
            z.writestr(name,data)
    manifest={'archive_sha256':sha(out),'files':{n:hashlib.sha256(b).hexdigest() for n,b in sorted(contents.items())}}
    Path('results/deploy/vakra-output-budget-v1-manifest.json').write_text(json.dumps(manifest,indent=2))
    receipt=json.dumps({'archive_sha256':sha(out),'files_verified':len(contents)},sort_keys=True).encode()
    Path('results/deploy/vakra-output-budget-v1-receipt-expected.json').write_bytes(receipt)
    print(json.dumps({'archive_bytes':out.stat().st_size,'members':len(contents),'sha256':sha(out),
                      'receipt_sha256':hashlib.sha256(receipt).hexdigest()}))


if __name__=='__main__':main()
