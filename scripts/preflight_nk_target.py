"""Verify real official tasks and frozen retrieval without claiming new memories exist."""
import json
from pathlib import Path

from autolab.local_smoke import sha256_file as sha
from autolab.nk_prefix_bank import NKMemoryBank
from autolab.nk_prefix_comparator import CONDITIONS
from autolab.tau2_native_baseline import verify_tau_source
from autolab.tau2_nk_transfer import verify_choices


def main():
    from tau2.runner.helpers import get_tasks
    root = Path('/xingjing/autoresearch-agent-papers')
    rev = Path(__file__).resolve().parent.parent
    reg = json.loads((rev / 'protocol/registration.json').read_bytes())
    selection_path = rev / 'protocol/selection.json'
    assert sha(selection_path) == reg['selection_sha256']
    selection = json.loads(selection_path.read_bytes())
    for name, expected in reg['source_files_sha256'].items():
        assert sha(rev / name) == expected
    tau = root / 'third_party/tau2-bench/tau2-bench'
    verify_tau_source(tau)
    for filename, key in [('tasks.json', 'tasks_file_sha256'), ('split_tasks.json', 'splits_file_sha256')]:
        assert sha(tau / 'data/tau2/domains/telecom' / filename) == reg[key]
    original = root / 'memory-banks/train-qwen3-cut8-v2.json'
    assert sha(original) == selection['original_source_bank_sha256']
    value = json.loads(original.read_bytes())
    ids = set(selection['selected_source_ids'])
    value['records'] = [r for r in value['records'] if r['record_id'] in ids]
    assert len(value['records']) == 70
    # Explicit empty placeholders only to check the selection plumbing. These
    # never enter a target run and are not saved as a curated bank.
    value['adaptation'] = 'autolab.nk_prefix_bank.v1'
    for record in value['records']:
        record['memories'] = {'raw': '', **{c: '' for c in CONDITIONS}}
        record['curation'] = {c: {'status': 'generation_error'} for c in CONDITIONS}
    bank = NKMemoryBank(value)
    tasks = get_tasks('telecom', task_split_name='test', num_tasks=40)
    assert not any('NL_ASSERTION' in str(t.evaluation_criteria.reward_basis) for t in tasks)
    for condition in CONDITIONS:
        assert len(verify_choices(tasks, bank, selection, condition)) == 40
    print(json.dumps({'official_tasks': 40, 'fixed_source_choices_checked': 80,
                      'selection_placeholder_only': True, 'curation_quality_checked': False,
                      'registered_target_episodes': 160, 'model_inference': False}))


if __name__ == '__main__':
    main()
