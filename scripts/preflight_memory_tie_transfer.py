"""Read-only official-task and bank checks before the registered test run."""
import hashlib
import json
from pathlib import Path

from autolab.experience_tie_audit import ORDERS, TieAuditMemoryBank
from autolab.local_smoke import sha256_file as sha
from autolab.tau2_native_baseline import verify_tau_source


def main():
    from tau2.runner.helpers import get_tasks
    root = Path('/xingjing/autoresearch-agent-papers')
    rev = Path(__file__).resolve().parent.parent
    reg = json.loads((rev / 'protocol/registration.json').read_bytes())
    tau = root / 'third_party/tau2-bench/tau2-bench'
    verify_tau_source(tau)
    for filename, key in [('tasks.json', 'tasks_file_sha256'), ('split_tasks.json', 'splits_file_sha256')]:
        assert sha(tau / 'data/tau2/domains/telecom' / filename) == reg[key]
    bank_path = root / 'memory-banks/train-qwen3-cut8-v2.json'
    assert sha(bank_path) == reg['source_bank_sha256']
    value = json.loads(bank_path.read_bytes())
    loaded = get_tasks('telecom', task_split_name='test', num_tasks=40)
    by_task_id = {t.id: t for t in loaded}
    assert len(loaded) == len(by_task_id) == 40 and set(by_task_id) == set(reg['selected_task_ids'])
    tasks = [by_task_id[uid] for uid in reg['selected_task_ids']]
    assert [t.id for t in tasks] == reg['selected_task_ids']
    records = {r['task_id']: r for r in reg['rows']}
    for order in ORDERS:
        bank = TieAuditMemoryBank(value, order)
        bank.assert_disjoint([t.id for t in tasks])
        for task in tasks:
            assert hashlib.sha256(task.ticket.encode()).hexdigest() == records[task.id]['ticket_sha256']
            assert 'NL_ASSERTION' not in str(task.evaluation_criteria.reward_basis)
            for condition in reg['memory_conditions']:
                result = bank.retrieve(task.ticket, condition)
                expected = records[task.id]['choices'][order]
                assert all(result[k] == expected[k] for k in expected)
    print(json.dumps({'official_tasks': 40, 'registered_episodes': 560, 'checked_choices': 240,
                      'source_bank_verified': True, 'source_target_disjoint': True, 'model_inference': False}))


if __name__ == '__main__':
    main()
