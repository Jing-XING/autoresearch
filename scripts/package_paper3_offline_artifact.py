"""Package an allowlisted, portable offline evidence snapshot; no credentials."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version',choices=('v1','v2','v3'),required=True)
    args=parser.parse_args()
    files={};aliases={}
    def add(name):
        p=Path(name)
        if not p.is_absolute():p=ROOT/p
        p=p.resolve();rel=p.relative_to(ROOT).as_posix()
        assert p.is_file() and (rel.startswith(('research/','scripts/','results/','output/pdf/')))
        assert p.suffix in ('.json','.jsonl','.py','.md','.bib','.zip','.pdf') or p.name=='LICENSE'
        assert not p.name.startswith('.env')
        files[rel]=p.read_bytes()
        if str(name)!=rel:aliases[str(name)]=rel
        return rel
    for name in ('manuscript.md','references.bib','claim_to_evidence.md','reproduce.md'):
        add('research/paper3/'+name)
    ledger=(ROOT/'research/paper3/claim_to_evidence.md').read_text(encoding='utf8')
    names=set(re.findall(r'`(?:\.\./evidence/)?([\w]+\.json)`',ledger))
    # Artifact's own receipt/verification is generated after packaging; no circular hash dependency.
    names={n for n in names if not n.startswith('paper3_offline_')}
    for name in sorted(names):add('research/evidence/'+name)
    for name in (
        'probe_rac_compensation_status.py','probe_rac_interceptor_recovery.py',
        'probe_rac_real_langchain_tools.py','probe_langchain_error_envelopes.py',
        'probe_rac_archived_rollback.py','probe_rac_mcp_discovery.py','probe_rac_real_mcp.py',
        'probe_rac_mcp_adapter_version.py','rac_mcp_fixture_server.py','validate_rac_mcp_probes.py',
        'probe_independent_compensation.py','validate_independent_compensation.py',
        'probe_tau_airline_compensation.py','tau_airline_compensation_fixture.py',
        'tau_airline_mcp_server.py','validate_tau_airline_compensation.py',
        'probe_tau_airline_retry_census.py','validate_tau_airline_retry_census.py',
        'audit_rac_zenodo_archive.py','verify_paper3_offline_artifact.py',
        'package_paper3_offline_artifact.py'):
        add('scripts/'+name)
    for name in (
        'research/native_airline_retry_protocol.md',
        'results/third_party/tau2-bench/data/tau2/domains/airline/db.json',
        'results/third_party/tau2-bench/LICENSE',
        'results/third_party/rac/zenodo-19753969.zip',
        'results/third_party/rac/zenodo-19753969.json'):
        add(name)
    def report(name):return json.loads((ROOT/'research/evidence'/name).read_bytes())
    r=report('tau_airline_compensation_probe_v1.json')
    for row in r['cases']:
        add(row['raw_state_file'])
        if 'wal_file' in row:add(row['wal_file'])
    r=report('independent_compensation_validation_v1.json')
    for name,digest in r['raw_sha256'].items():
        rel=add(name);assert sha(files[rel])==digest
    r=report('rac_real_mcp_probe_v1.json')
    for i,row in enumerate(r['cases']):
        name=Path(r['raw_fixture_directory'])/f'case-{i:02d}.json'
        rel=add(str(name));assert sha(files[rel])==row['state_sha256']
    # Resolve only known saved fixture hashes, never scan arbitrary user directories.
    needed={report('rac_mcp_discovery_probe_v1.json')['state_sha256']}
    needed.update(r['state_sha256'] for r in report('rac_mcp_adapter_version_probe_v1.json')['cases'])
    found=set()
    for p in (ROOT/'results/probes/rac-mcp').rglob('*.json'):
        digest=sha(p.read_bytes())
        if digest in needed: add(str(p));found.add(digest)
    assert found==needed
    r=report('tau_airline_retry_census_v1.json');rel=add(r['raw']);assert sha(files[rel])==r['raw_sha256']
    if args.version=='v3':
        for name in ('research/evidence/native_retail_composition_package_v1.json',
                     'research/native_retail_composition_protocol_v1.md',
                     'scripts/probe_tau_retail_payment_cancel_v1.py',
                     'scripts/verify_tau_retail_composition_v1.py',
                     'scripts/build_review_pdf.py',
                     'output/pdf/paper3-recovery-interfaces-review.pdf',
                     'output/pdf/paper3-recovery-interfaces-review.build.json',
                     'results/deploy/native-retail-composition-v1.zip',
                     'results/remote/native-retail-composition-v1-results.zip'):
            add(name)
    manifest=dict(format='paper3-offline-v2' if args.version=='v3' else 'paper3-offline-v1',
        scope='Byte-integrity inspection plus offline reanalysis of native airline25, retrycensus2000, publishedarchive280'+(', and native retail543 paths/663 calls' if args.version=='v3' else '')+'. Other reports are inspection-only; no native/model reexecution.',
        original_path_aliases=aliases,
        files={n:dict(bytes=len(b),sha256=sha(b)) for n,b in sorted(files.items())})
    archive=ROOT/f'results/remote/paper3-offline-evidence-{args.version}.zip'
    with ZipFile(archive,'x',ZIP_DEFLATED) as z:
        for name,data in sorted(files.items()):z.writestr(name,data)
        z.writestr('artifact_manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    with ZipFile(archive) as z:
        assert z.testzip() is None
        assert all(z.read(n)==b for n,b in files.items())
    receipt=dict(archive=archive.relative_to(ROOT).as_posix(),bytes=archive.stat().st_size,
        sha256=sha(archive.read_bytes()),payload_members=len(files),total_entries=len(files)+1,
        manifest_sha256=sha(json.dumps(manifest,ensure_ascii=False,indent=2).encode()+b'\n'),
        verifier_sha256=sha(files['scripts/verify_paper3_offline_artifact.py']),
        manuscript_sha256=sha(files['research/paper3/manuscript.md']),scope=manifest['scope'])
    with (ROOT/f'research/evidence/paper3_offline_artifact_receipt_{args.version}.json').open('x',encoding='utf8') as f:
        json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps(receipt))


if __name__=='__main__':main()
