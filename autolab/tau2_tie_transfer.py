"""Execute the frozen test-split instruction and tied-source sensitivity study."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import traceback

from .experience_memory_bank import FixedMemoryBank
from .experience_tie_audit import ORDERS, TieAuditMemoryBank
from .local_smoke import sha256_file as sha
from .native_tool_agent import NativeTransformersModel
from .tau2_native_agent import register_native_solo
from .tau2_native_baseline import verify_tau_source
from .tool_agent import write_episode


def main():
    from tau2.data_model.simulation import TextRunConfig
    from tau2.evaluator.evaluator import EvaluationType
    from tau2.runner.batch import run_single_task
    from tau2.runner.helpers import get_tasks

    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('model-path', 'output', 'tau-repo', 'registration', 'memory-bank'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--model', choices=('qwen3', 'qwen25'), required=True)
    parser.add_argument('--condition', choices=('none', 'full_metadata', 'boundary_aware'), required=True)
    parser.add_argument('--tie-order', choices=ORDERS, default='record_id')
    parser.add_argument('--shard', type=int, choices=(0, 1), required=True)
    args = parser.parse_args()
    registration = json.loads(args.registration.read_bytes())
    assert registration['batch'] == 'tau-memory-test40-ties-v1'
    assert registration['registered_episodes'] == 560 and registration['target_outputs_seen'] is False
    assert args.condition != 'none' or args.tie_order == 'record_id'
    tau_digest = verify_tau_source(args.tau_repo)
    for filename, field in [('tasks.json', 'tasks_file_sha256'), ('split_tasks.json', 'splits_file_sha256')]:
        assert sha(args.tau_repo / 'data/tau2/domains/telecom' / filename) == registration[field]
    assert sha(args.memory_bank) == registration['source_bank_sha256']
    for filename, digest in registration['source_files_sha256'].items():
        assert sha(Path(__file__).resolve().parent.parent / filename) == digest
    bank_value = json.loads(args.memory_bank.read_bytes())
    loaded = get_tasks('telecom', task_split_name='test', num_tasks=40)
    by_task_id = {t.id: t for t in loaded}
    assert len(loaded) == len(by_task_id) == 40 and set(by_task_id) == set(registration['selected_task_ids'])
    tasks = [by_task_id[uid] for uid in registration['selected_task_ids']]
    assert [t.id for t in tasks] == registration['selected_task_ids']
    FixedMemoryBank(bank_value).assert_disjoint([t.id for t in tasks])
    bank = None if args.condition == 'none' else TieAuditMemoryBank(bank_value, args.tie_order)
    by_id = {r['task_id']: r for r in registration['rows']}
    for task in tasks:
        assert hashlib.sha256(task.ticket.encode()).hexdigest() == by_id[task.id]['ticket_sha256']
        if bank:
            choice = bank.retrieve(task.ticket, args.condition)
            expected = by_id[task.id]['choices'][args.tie_order]
            assert all(choice[k] == expected[k] for k in expected)
    selected = tasks[args.shard::2]
    args.output.mkdir(parents=True, exist_ok=False)
    source_names = ['tau2_native_agent.py', 'tau2_native_baseline.py', 'tau2_tie_transfer.py',
                    'native_tool_agent.py', 'local_smoke.py', 'experience_memory_bank.py',
                    'experience_tie_audit.py', 'experience_curator.py', 'trajectory_cutoffs.py']
    manifest = {'purpose': __doc__, 'batch': registration['batch'], 'model': args.model,
                'task_split': 'test', 'all_task_ids': [t.id for t in tasks],
                'selected_task_ids': [t.id for t in selected], 'shard': args.shard, 'shards': 2,
                'condition': args.condition, 'tie_order': args.tie_order,
                'registration_sha256': sha(args.registration), 'memory_bank_sha256': sha(args.memory_bank),
                'tau_source_manifest_sha256': tau_digest, 'seed': 20260919,
                'decoder': 'greedy_native_template_tool_prefix', 'supplied_prefix': '<tool_call>\n',
                'max_new_tokens': 512, 'max_steps': 60, 'max_errors': 5,
                'task_sha256': {t.id: hashlib.sha256(t.model_dump_json().encode()).hexdigest() for t in selected},
                'source_sha256': {n: sha(Path(__file__).parent / n) for n in source_names},
                'packages': {n: importlib.metadata.version(n) for n in ('torch', 'transformers', 'tau2', 'litellm')},
                'model_files_sha256': {p.name: sha(p) for p in sorted(args.model_path.iterdir())
                                       if p.is_file() and (p.suffix in ('.json', '.safetensors') or p.name == 'merges.txt')}}
    write_episode(manifest, args.output, 'manifest')
    model = NativeTransformersModel(args.model_path, tool_prefix=True)
    audit = []
    name = register_native_solo(model, audit, memory_bank=bank,
                               memory_condition=None if bank is None else args.condition)
    config = TextRunConfig(domain='telecom', agent=name, user=name + '_dummy', llm_agent=str(args.model_path),
                           max_steps=60, max_errors=5, seed=20260919, enforce_communication_protocol=True)
    write_episode(config.model_dump(mode='json'), args.output, 'config')
    rows = []
    for index, task in enumerate(selected):
        audit.clear()
        try:
            result = run_single_task(config, task, seed=20260919, evaluation_type=EvaluationType.ALL)
            write_episode(result.model_dump(mode='json'), args.output, f'case-{index:03d}')
            row = {'task_id': task.id, 'reward': result.reward_info.reward,
                   'termination': result.termination_reason.value, 'model_calls': len(audit)}
        except Exception as exc:
            row = {'task_id': task.id, 'reward': None, 'error_type': type(exc).__name__,
                   'error': str(exc), 'traceback': traceback.format_exc(), 'model_calls': len(audit)}
        finally:
            write_episode({'task_id': task.id, 'calls': audit}, args.output, f'case-{index:03d}-model-audit')
        rows.append(row)
        write_episode(row, args.output, f'case-{index:03d}-status')
        print(json.dumps(row), flush=True)
    write_episode({'purpose': __doc__, 'n': len(rows), 'rows': rows,
                   'successes': sum(r['reward'] == 1 for r in rows),
                   'errors': sum(r['reward'] is None for r in rows)}, args.output, 'summary')
    print('REGISTERED_TIE_TRANSFER_COMPLETE', flush=True)


if __name__ == '__main__':
    main()
