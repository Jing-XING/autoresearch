"""Evaluate both frozen NK-schema curators on the same 40 official test tasks."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import traceback

from .local_smoke import sha256_file as sha
from .nk_prefix_bank import NKMemoryBank
from .nk_prefix_comparator import CONDITIONS
from .tool_agent import write_episode


def verify_choices(tasks, bank, selection, condition):
    ids = [r['task_id'] for r in selection['rows']]
    by_id = {t.id: t for t in tasks}
    if len(tasks) != len(by_id) or set(by_id) != set(ids):
        raise ValueError('Official task coverage differs from frozen selection')
    bank.assert_disjoint(ids)
    ordered = [by_id[uid] for uid in ids]
    for task, row in zip(ordered, selection['rows']):
        if hashlib.sha256(task.ticket.encode()).hexdigest() != row['ticket_sha256']:
            raise ValueError('Visible target ticket changed')
        result = bank.retrieve(task.ticket, condition)
        if any(result[k] != v for k, v in row['source_choice'].items()):
            raise ValueError('Source selection differs from frozen choice')
    return ordered


def main():
    from tau2.data_model.simulation import TextRunConfig
    from tau2.evaluator.evaluator import EvaluationType
    from tau2.runner.batch import run_single_task
    from tau2.runner.helpers import get_tasks
    from .native_tool_agent import NativeTransformersModel
    from .tau2_native_agent import register_native_solo
    from .tau2_native_baseline import verify_tau_source

    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('model-path', 'output', 'tau-repo', 'registration', 'selection', 'memory-bank'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--model', choices=('qwen3', 'qwen25'), required=True)
    parser.add_argument('--condition', choices=CONDITIONS, required=True)
    parser.add_argument('--shard', type=int, choices=(0, 1), required=True)
    parser.add_argument('--preflight-only', action='store_true')
    args = parser.parse_args()
    reg = json.loads(args.registration.read_bytes())
    if reg['batch'] != 'tau-nk-test40-v1' or reg['registered_episodes'] != 160:
        raise ValueError('Unknown target registration')
    if sha(args.selection) != reg['selection_sha256']:
        raise ValueError('Frozen selection changed')
    selection = json.loads(args.selection.read_bytes())
    root = Path(__file__).resolve().parent.parent
    for filename, expected in reg['source_files_sha256'].items():
        if sha(root / filename) != expected:
            raise ValueError('Target source file changed: ' + filename)
    tau_digest = verify_tau_source(args.tau_repo)
    for filename, key in [('tasks.json', 'tasks_file_sha256'), ('split_tasks.json', 'splits_file_sha256')]:
        if sha(args.tau_repo / 'data/tau2/domains/telecom' / filename) != reg[key]:
            raise ValueError('Official task data changed')
    value = json.loads(args.memory_bank.read_bytes())
    if value['curation_registration_sha256'] != reg['curation_registration_sha256']:
        raise ValueError('Bank was not built from registered curation')
    if value['preparation_manifest_sha256'] != selection['preparation_manifest_sha256']:
        raise ValueError('Bank prepared inputs changed')
    if sorted(r['record_id'] for r in value['records']) != selection['selected_source_ids']:
        raise ValueError('Eligible source pool changed')
    bank = NKMemoryBank(value)
    loaded = get_tasks('telecom', task_split_name='test', num_tasks=40)
    tasks = verify_choices(loaded, bank, selection, args.condition)
    if any('NL_ASSERTION' in str(t.evaluation_criteria.reward_basis) for t in tasks):
        raise ValueError('Unexpected model-based reward component')
    selected = tasks[args.shard::2]
    if args.preflight_only:
        print(json.dumps({'official_tasks': len(tasks), 'shard_tasks': len(selected),
                          'fixed_source_choices_verified': True, 'model_inference': False}))
        return
    model_hashes = {p.name: sha(p) for p in sorted(args.model_path.iterdir())
                   if p.is_file() and (p.suffix in ('.json', '.safetensors') or p.name == 'merges.txt')}
    if model_hashes != reg['model_files_sha256'][args.model]:
        raise ValueError('Target checkpoint changed')
    manifest = {'purpose': __doc__, 'batch': reg['batch'], 'model': args.model,
                'task_split': 'test', 'all_task_ids': [t.id for t in tasks],
                'selected_task_ids': [t.id for t in selected], 'shard': args.shard, 'shards': 2,
                'condition': args.condition, 'registration_sha256': sha(args.registration),
                'selection_sha256': sha(args.selection), 'memory_bank_sha256': sha(args.memory_bank),
                'tau_source_manifest_sha256': tau_digest, 'seed': 20260919,
                'decoder': 'greedy_native_template_tool_prefix', 'supplied_prefix': '<tool_call>\n',
                'max_new_tokens': 512, 'max_steps': 60, 'max_errors': 5,
                'task_sha256': {t.id: hashlib.sha256(t.model_dump_json().encode()).hexdigest() for t in selected},
                'source_sha256': reg['source_files_sha256'], 'model_files_sha256': model_hashes,
                'packages': {n: importlib.metadata.version(n) for n in ('torch', 'transformers', 'tau2', 'litellm')}}
    args.output.mkdir(parents=True, exist_ok=False)
    write_episode(manifest, args.output, 'manifest')
    model = NativeTransformersModel(args.model_path, tool_prefix=True)
    audit = []
    name = register_native_solo(model, audit, memory_bank=bank, memory_condition=args.condition)
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


if __name__ == '__main__':
    main()
