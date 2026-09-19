"""Replay recorded observations through a passive ledger; never invoke tools."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from autolab.tool_evidence_ledger import EvidenceLedger


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    rows=[]
    for file in sorted(a.root.glob('*/*/shard-0/case-*.json')):
        case=json.loads(file.read_bytes())
        names=[t['function']['name'] for t in case['tools']]
        ledger=EvidenceLedger(case['initial_peek'],case['uuid'],names)
        for step in case['trace']:
            if 'tool_result' in step:
                ledger.observe(step['tool_call'],step['tool_result'])
        rows.append({'source':file.relative_to(a.root).as_posix(),
                     'source_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
                     'uuid':case['uuid'],'ledger':ledger.snapshot()})
    assert len(rows)==48,'Expected the complete frozen development grid'
    flags=Counter(e['status'] for r in rows for e in r['ledger']['events'])
    out={'purpose':'passive observation audit; no model intervention or correctness score',
         'limitations':['Completeness records direct previews/getters per handle only; no inference across parent/child columns.',
                       'Partial direct observation does not prove the answer is unidentifiable from the full history.',
                       'Recorded tool semantics and cardinalities are trusted; natural-language scope is not verified.',
                       'Unknown transformations intentionally lose lineage rather than pretending earlier predicates survive.'],
         'implementation_sha256':hashlib.sha256(Path('autolab/tool_evidence_ledger.py').read_bytes()).hexdigest(),
         'episodes':len(rows),'observation_statuses':dict(flags),'rows':rows}
    with a.output.open('x',encoding='utf-8') as f:json.dump(out,f,ensure_ascii=False,indent=2)
    print(json.dumps({'episodes':len(rows),'observation_statuses':dict(flags)}))


if __name__=='__main__':
    main()
