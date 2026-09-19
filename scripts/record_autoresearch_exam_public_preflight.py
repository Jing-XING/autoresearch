"""Join the actual remote public-input preflight to its immutable deployment."""
from pathlib import Path
from zipfile import ZipFile
import hashlib
import json


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    specs=Path('research/evidence/autoresearch_exam_task_specs_v1.json')
    data=json.loads(specs.read_bytes())
    cpu=[r['task'] for r in data['task_specs'] if r['spec']['environment']['gpus']==0]
    gpu=[r['task'] for r in data['task_specs'] if r['spec']['environment']['gpus']>0]
    assert len(cpu)==22 and len(gpu)==7
    assert all((r['spec']['environment']['cpus'],r['spec']['environment']['memory_mb'],r['spec']['environment']['storage_mb'])==(8,14336,153600) for r in data['task_specs'] if r['task'] in cpu)
    assert all(r['spec']['environment']['gpu_types']==['H100'] for r in data['task_specs'] if r['task'] in gpu)
    pins={}
    for task in ('label-efficient-risk-estimator','carps-star-discrepancy-subset-select','shortest-valid-ci-l2-ece'):
        p=Path('results/third_party/autoresearch-exam-tasks/source')/task/'environment/requirements.txt'
        pins[task]=dict(requirements=p.read_text(encoding='utf8').splitlines(),sha256=sha(p))
    archive=Path('results/deploy/autoresearch-exam-public-preflight-v1.zip')
    report=Path('research/evidence/autoresearch_exam_public_input_preflight_v1.json')
    remote=Path('results/remote/autoresearch-exam-public-input-report-v1.json')
    assert report.read_bytes()==remote.read_bytes()
    r=json.loads(report.read_bytes());assert r['status']=='public-input-preflight-passed'
    assert (r['files_verified'],r['ci_generator_calls'],r['model_calls'],r['grader_calls'])==(202,48,0,0)
    for name,h in r['input_manifest_sha256'].items():assert sha(Path('research/evidence')/name)==h
    assert r['script_sha256']==sha(Path('scripts/preflight_autoresearch_exam_public_inputs.py'))
    with ZipFile(archive) as z:
        manifest=json.loads(z.read('package_files.json'))
        assert len(manifest)==205 and len(z.namelist())==206 and z.testzip() is None
        assert all(hashlib.sha256(z.read(n)).hexdigest()==h==sha(Path(n)) for n,h in manifest.items())
    receipt=dict(scope='Acquisition plus executed public-input preflight on the designated server. Not official grader/model execution. No queued experiment changed.',
        archive=archive.as_posix(),archive_bytes=archive.stat().st_size,archive_sha256=sha(archive),payload_members=205,total_entries=206,
        remote_directory='/xingjing/autoresearch-agent-papers/preflights/autoresearch-exam-public-v1',
        report_sha256=sha(report),transfer_receipt_sha256=sha(Path('results/remote/autoresearch-exam-public-preflight-v1-receipt.json')),
        preflight_script_sha256=r['script_sha256'],public_specs_sha256=sha(specs),public_assets_sha256=sha(Path('research/evidence/autoresearch_exam_public_assets_v1.json')),
        cpu_only_tasks=cpu,h100_tasks=gpu,original_task_runtime_requirements=pins,observed_numpy=r['numpy'],
        remote_container_observation=dict(docker_cli=None,docker_socket_present=False,logical_cpus_not_effective_quota=64,disk_free_gib_snapshot=4520.5),
        runtime_limits=['Remote NumPy2.5.3 differs from the exact per-task pins recorded above.','SciPy not tested.','No official container, evaluator, reward or autonomous model experiment executed.'],
        documentation_correction='An initial local receipt assertion incorrectly grouped the subset task with the risk task at NumPy2.3.2. Reading the actual pinned requirements corrected this to2.5.2 before receipt publication; no remote preflight rerun or data change.',
        script_sha256=sha(Path(__file__)))
    with Path('research/evidence/autoresearch_exam_public_preflight_deployment_v1.json').open('x',encoding='utf8') as f:
        json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps(dict(cpu_tasks=len(cpu),h100_tasks=len(gpu),package_members=206,report_verified=True)))


if __name__=='__main__':main()
