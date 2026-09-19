"""Join existing strict state replay with offline cuts; no new model or replay execution.

Hidden state labels remain evaluator-only and do not alter the frozen memory bank.
"""
import hashlib
import json
from pathlib import Path


def main():
    audit_path = Path('research/evidence/tau_train74_qwen3_state_audit.json')
    cut_root = Path('results/remote/tau-train74-qwen3-curation-v1/cutoffs/train-qwen3-v1')
    manifest_path = cut_root / 'manifest.json'
    bank_path = Path('results/remote/tau-train74-qwen3-curation-v2/memory-banks/train-qwen3-cut8-v2.json')
    sha = lambda data: hashlib.sha256(data).hexdigest()
    audit, manifest, bank = [json.loads(p.read_bytes()) for p in (audit_path, manifest_path, bank_path)]
    assert sha(manifest_path.read_bytes()) == bank['source_manifest_sha256']
    by_task = {r['task_id']: r for r in audit['rows']}
    assert len(by_task) == 74 and not audit['unscored_runs']
    rows = []
    for cut in manifest['records']:
        row = by_task[cut['cluster_id']]
        assert row['status_file'] == cut['source']
        assert audit['input_sha256'][cut['source'].replace('-status.json', '.json')] == cut['simulation_sha256']
        payload = json.loads((cut_root / 'inputs' / (cut['record_id'] + '.json')).read_bytes())
        digest = sha(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode())
        assert digest == cut['payload_sha256']
        prefix = [r for r in row['prefixes'] if r['generation_count'] <= cut['cutoff']][-1]
        assert prefix['generation_count'] == payload['observed_generations']
        external = payload['stop_reason'] == 'external_generation_cutoff'
        expected_reward = 0.0 if external else row['official_reward']
        assert payload['observed_benchmark_reward'] == expected_reward
        rows.append(dict(record_id=cut['record_id'], cutoff=cut['cutoff'],
            external_cut=external, state_and_action_satisfied=prefix['task_satisfied'],
            supplied_completion_reward=expected_reward, recorded_full_reward=row['official_reward']))
    summaries = []
    for cutoff in sorted({r['cutoff'] for r in rows}):
        selected = [r for r in rows if r['cutoff'] == cutoff]
        assert len(selected) == 74
        external = [r for r in selected if r['external_cut']]
        summaries.append(dict(cutoff=cutoff, sources=len(selected), externally_cut=len(external),
            external_already_satisfied=sum(r['state_and_action_satisfied'] for r in external),
            external_recorded_continuation_succeeds=sum(r['recorded_full_reward'] == 1 for r in external),
            external_unsatisfied_then_recorded_success=sum(not r['state_and_action_satisfied'] and r['recorded_full_reward'] == 1 for r in external),
            original_end_satisfied=sum(r['state_and_action_satisfied'] for r in selected if not r['external_cut'])))
    report = dict(purpose=__doc__, input_sha256={str(p):sha(p.read_bytes()) for p in (audit_path,manifest_path,bank_path)},
        script_sha256=sha(Path(__file__).read_bytes()), source_replay_manifest_hash=audit['tau_source_sha256'],
        rows=rows, summaries=summaries,
        cutoff8_external_already_satisfied_ids=[r['record_id'] for r in rows if r['cutoff']==8 and r['external_cut'] and r['state_and_action_satisfied']],
        interpretation='Offline imposed cut, not a naturally observed termination failure. Official rewards and target inputs remain unchanged. Existing evaluator labels are joined, not newly replayed.')
    with Path('research/evidence/memory_cutoff_satisfaction_join_v1.json').open('x',encoding='utf-8') as stream:
        json.dump(report,stream,indent=2)
        stream.write('\n')
    print(json.dumps(summaries))


if __name__ == '__main__':
    main()
