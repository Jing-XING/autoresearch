"""Bounded public tau2 solo development run with the official environment evaluator."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import traceback

from autolab.local_smoke import sha256_file
from autolab.native_tool_agent import NativeTransformersModel
from autolab.tau2_native_agent import register_native_solo
from autolab.tool_agent import write_episode


def verify_tau_source(root):
    import tau2
    if not Path(tau2.__file__).resolve().is_relative_to(root.resolve()):
        raise ValueError("Imported tau2 does not match the requested source directory")
    files = []
    for name in ["src", "data/tau2/domains", "data/tau2/user_simulator", "data/tau2/user_simulation"]:
        files.extend(p for p in (root / name).rglob("*") if p.is_file() and "__pycache__" not in str(p))
    files += [root / n for n in ["pyproject.toml", "README.md", "LICENSE"] if (root / n).exists()]
    hashes = {p.relative_to(root).as_posix(): sha256_file(p) for p in files}
    digest = hashlib.sha256(json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if digest != "d07cc342f43894f866d1fd151fdd1ed996976cb194299e2d87913bc5bc8ee349":
        raise ValueError(f"Official source/data hash mismatch: {digest}")
    return digest


def main():
    from tau2.data_model.simulation import TextRunConfig
    from tau2.evaluator.evaluator import EvaluationType
    from tau2.runner.batch import run_single_task
    from tau2.runner.helpers import get_tasks

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model-path", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--tau-repo", type=Path, required=True)
    p.add_argument("--split", default="small", choices=["small", "train"])
    p.add_argument("--count", type=int, default=4)
    p.add_argument("--max-steps", type=int, default=60)
    p.add_argument("--shard", type=int, default=0)
    p.add_argument("--shards", type=int, default=1)
    p.add_argument("--tool-prefix", action="store_true", help="Supply an opening tool-call marker; formatting baseline, not full grammar constraints")
    args = p.parse_args()
    if args.count < 1 or args.shards < 1 or not 0 <= args.shard < args.shards:
        p.error("Invalid count/shard")
    tau_digest = verify_tau_source(args.tau_repo)
    args.output.mkdir(parents=True, exist_ok=False)
    tasks = get_tasks("telecom", task_split_name=args.split, num_tasks=args.count)
    if len(tasks) != args.count:
        raise ValueError("Requested task count unavailable")
    # This batch is explicitly development. Do not tune on a held-out split here.
    selected = tasks[args.shard::args.shards]
    manifest = {
        "purpose": "public_benchmark_development_only", "domain": "telecom", "protocol": "official_solo",
        "task_split": args.split, "all_task_ids": [t.id for t in tasks], "selected_task_ids": [t.id for t in selected],
        "selection": "fixed source order, then deterministic stride; no outcome filtering",
        "seed": 20260919, "decoder": "greedy_native_template_tool_prefix" if args.tool_prefix else "greedy_native_template", "max_new_tokens": 512,
        "supplied_prefix": "<tool_call>\n" if args.tool_prefix else "",
        "max_steps": args.max_steps, "max_errors": 5,
        "tau_commit": "b7ea9074c1cba482b30687fecdb5c8425fd6f619",
        "tau_source_manifest_sha256": tau_digest,
        "packages": {n: importlib.metadata.version(n) for n in ["torch", "transformers", "tau2", "litellm"]},
        "source_sha256": {n: sha256_file(Path(__file__).parent / n) for n in
                          ["tau2_native_agent.py", "tau2_native_baseline.py", "native_tool_agent.py", "local_smoke.py"]},
        "model_files_sha256": {p.name: sha256_file(p) for p in sorted(args.model_path.iterdir())
                                if p.is_file() and (p.suffix in [".json", ".safetensors"] or p.name == "merges.txt")},
        "task_sha256": {t.id: hashlib.sha256(t.model_dump_json().encode()).hexdigest() for t in selected},
    }
    write_episode(manifest, args.output, "manifest")
    model = NativeTransformersModel(args.model_path, tool_prefix=args.tool_prefix)
    audit = []
    agent_name = register_native_solo(model, audit)
    config = TextRunConfig(domain="telecom", agent=agent_name, user=agent_name + "_dummy",
                           llm_agent=str(args.model_path), max_steps=args.max_steps,
                           max_errors=5, seed=20260919, enforce_communication_protocol=True)
    write_episode(config.model_dump(mode="json"), args.output, "config")
    rows = []
    for index, task in enumerate(selected):
        audit.clear()
        try:
            result = run_single_task(config, task, seed=20260919, evaluation_type=EvaluationType.ALL)
            write_episode(result.model_dump(mode="json"), args.output, f"case-{index:03d}")
            row = {"task_id": task.id, "reward": result.reward_info.reward,
                   "termination": result.termination_reason.value, "model_calls": len(audit)}
        except Exception as exc:
            row = {"task_id": task.id, "reward": None, "error_type": type(exc).__name__,
                   "error": str(exc), "traceback": traceback.format_exc(), "model_calls": len(audit)}
        finally:
            write_episode({"task_id": task.id, "calls": audit}, args.output, f"case-{index:03d}-model-audit")
        rows.append(row)
        write_episode(row, args.output, f"case-{index:03d}-status")
        print(json.dumps(row), flush=True)
    write_episode({"purpose": "development_only", "n": len(rows), "rows": rows,
                   "successes": sum(r["reward"] == 1 for r in rows),
                   "errors": sum(r["reward"] is None for r in rows)}, args.output, "summary")
    print("TAU2_NATIVE_BASELINE_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
