"""Audit complete native tau2 batches without discarding failed model runs."""
from collections import Counter
import hashlib
import json
from pathlib import Path


def read(path):
    return json.loads(path.read_bytes())


def summarize(root, expected_models=("qwen3", "qwen25")):
    rows, fingerprints, model_tasks, references = [], {}, {}, {}
    for manifest_path in sorted(root.glob("*/shard-*/manifest.json")):
        shard = manifest_path.parent
        model = shard.parent.name
        manifest = read(manifest_path)
        config = read(shard / "config.json") if (shard / "config.json").exists() else {}
        if model not in expected_models:
            raise ValueError("Unexpected model outside registered model pool")
        reference = {k: manifest[k] for k in ("all_task_ids", "seed", "decoder",
                     "max_new_tokens", "max_steps", "max_errors", "tau_commit",
                     "tau_source_manifest_sha256", "source_sha256", "task_split")}
        reference.update({k: manifest.get(k) for k in ("memory_bank_sha256", "memory_condition")})
        if references and reference != next(iter(references.values())):
            raise ValueError("Incompatible task, adapter or inference configuration across shards")
        references[model] = reference
        if model in model_tasks and model_tasks[model]["weights"] != manifest["model_files_sha256"]:
            raise ValueError("Model weights differ across same-model shards")
        record = model_tasks.setdefault(model, {"seen": set(), "weights": manifest["model_files_sha256"]})
        for index, task_id in enumerate(manifest["selected_task_ids"]):
            if task_id in record["seen"]:
                raise ValueError("Duplicate task within model")
            record["seen"].add(task_id)
            status_path = shard / f"case-{index:03d}-status.json"
            if not status_path.exists():
                rows.append({"model": model, "task_id": task_id, "pending": True})
                continue
            status = read(status_path)
            audit_path = shard / f"case-{index:03d}-model-audit.json"
            audit = read(audit_path)
            if status["task_id"] != task_id or audit["task_id"] != task_id:
                raise ValueError("Task identity mismatch between manifest and artifacts")
            if len(audit["calls"]) != status["model_calls"]:
                raise ValueError("Model-call count mismatch")
            usage = Counter()
            errors = []
            for call in audit["calls"]:
                digest = hashlib.sha256(json.dumps(call["input"], sort_keys=True).encode()).hexdigest()
                if digest != call["input_sha256"]:
                    raise ValueError("Model-input hash mismatch")
                usage.update({k: call["reply"][k] for k in ("input_tokens", "output_tokens", "elapsed_seconds")})
                if "protocol_error" in call:
                    errors.append(call["protocol_error"])
            if status["reward"] is not None:
                simulation = read(shard / f"case-{index:03d}.json")
                if simulation["task_id"] != task_id or simulation["reward_info"]["reward"] != status["reward"]:
                    raise ValueError("Official simulation/status reward mismatch")
            rows.append({"model": model, **status, "usage": dict(usage), "protocol_errors": errors,
                         "model_path": config.get("llm_agent")})
        for path in sorted(shard.glob("*.json")):
            fingerprints[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    if not references:
        raise ValueError("No manifests found")
    groups = []
    for model, record in model_tasks.items():
        expected = set(references[model]["all_task_ids"])
        if record["seen"] - expected:
            raise ValueError("Unexpected task outside registered task pool")
        actual = [r for r in rows if r["model"] == model and not r.get("pending")]
        successes = sum(r["reward"] == 1 for r in actual)
        groups.append({"model": model, "expected_n": len(expected), "completed_n": len(actual),
                       "missing_task_ids": sorted(expected - {r["task_id"] for r in actual}),
                       "successes": successes, "run_errors": sum(r["reward"] is None for r in actual),
                       "protocol_error_runs": sum(bool(r["protocol_errors"]) for r in actual),
                       "success_fraction_all_registered_tasks": successes / len(expected)})
    missing_models = sorted(set(expected_models) - model_tasks.keys())
    return {"purpose": "public_development_only", "complete": not missing_models and all(not g["missing_task_ids"] for g in groups),
            "missing_models": missing_models,
            "groups": groups, "rows": rows, "configuration": next(iter(references.values())),
            "artifact_sha256": fingerprints,
            "limitations": "Small development pool, greedy decoding, no significance or method-superiority claim."}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    print(json.dumps(summarize(parser.parse_args().root), indent=2))
