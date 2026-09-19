"""Paired resource-cutoff screening, not a public benchmark or paper result."""
import argparse
from dataclasses import asdict
import importlib.metadata
import json
from pathlib import Path

from autolab.local_smoke import sha256_file
from autolab.memory_pilot import SQLTask
from autolab.native_tool_agent import NativeTransformersModel, SQL_TOOLS, run_native_episode
from autolab.tool_agent import Budget, write_episode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--shard", type=int, default=0)
    parser.add_argument("--shards", type=int, default=4)
    args = parser.parse_args()
    if args.shards < 1 or not 0 <= args.shard < args.shards:
        parser.error("invalid shard")
    output = args.output / f"shard-{args.shard}"
    output.mkdir(parents=True, exist_ok=False)
    metadata = {
        "purpose": "synthetic_paired_development_screening_only",
        "model_path": str(args.model_path), "seed": 20260919,
        "decoder": "greedy_native_tool_template", "shard": args.shard,
        "packages": {n: importlib.metadata.version(n) for n in ["torch", "transformers", "accelerate"]},
        "source_sha256": {n: sha256_file(Path(__file__).parent / n) for n in
                          ["native_memory_pilot.py", "native_tool_agent.py", "local_smoke.py", "memory_pilot.py"]},
        "tokenizer_config_sha256": sha256_file(args.model_path / "tokenizer_config.json"),
        "cases": list(range(args.shard, 12, args.shards)),
        "source_tool_budgets": [2, 4], "target_budget": asdict(Budget(10, 7, 384)),
        "conditions": ["none", "raw", "reflection", "scoped"],
    }
    write_episode(metadata, output, "manifest")
    model = NativeTransformersModel(args.model_path)
    rows = []
    for case in metadata["cases"]:
        for limit in metadata["source_tool_budgets"]:
            prefix = f"case-{case:02d}-budget-{limit}"
            source = SQLTask(7000 + case, case)
            source_budget = Budget(6, limit, 384)
            result = run_native_episode(model, source, source.task, source_budget,
                                        {**metadata, "case": case, "phase": "source"}, SQL_TOOLS)
            write_episode(result, output, prefix + "-source")
            source.db.close()
            # Equal observed evidence for both curators; never disclose expected answers.
            evidence = {"task": source.task, "trace": result["trace"],
                        "budget": asdict(source_budget), "termination": result["termination"],
                        "success": result["evaluation"]["success"]}
            memories = {"none": "", "raw": json.dumps(evidence)}
            for condition, instruction in [
                ("reflection", "Write a concise reusable lesson from this experience for related future tasks."),
                ("scoped", "Write a concise reusable lesson. State what the observations establish, distinguish resource cutoff from method failure, and specify when a different task budget would invalidate any negative conclusion.")]:
                reply = model.generate([
                    {"role": "system", "content": instruction + " Do not invent evidence or future answers."},
                    {"role": "user", "content": json.dumps(evidence)}], 256)
                memories[condition] = reply.text
                write_episode({"metadata": metadata, "case": case, "source_tool_budget": limit,
                               "condition": condition, "evidence": evidence,
                               "instruction": instruction, "reply": asdict(reply)},
                              output, prefix + "-memory-" + condition)
            for condition, memory in memories.items():
                target = SQLTask(9000 + case, case)
                trial = run_native_episode(model, target, target.task, Budget(10, 7, 384),
                                           {**metadata, "case": case, "phase": "target",
                                            "source_tool_budget": limit, "condition": condition},
                                           SQL_TOOLS, memory)
                write_episode(trial, output, prefix + "-target-" + condition)
                target.db.close()
                row = {"case": case, "source_tool_budget": limit, "condition": condition,
                       "source_success": result["evaluation"]["success"],
                       "source_termination": result["termination"],
                       "success": trial["evaluation"]["success"], "termination": trial["termination"],
                       "usage": trial["usage"],
                       "protocol_errors": sum("protocol_error" in t for t in trial["trace"])}
                rows.append(row)
                print(json.dumps(row), flush=True)
    write_episode({"purpose": "development_only", "rows": rows}, output, "summary")
    print("NATIVE_PAIRED_PILOT_COMPLETE", args.shard, flush=True)


if __name__ == "__main__":
    main()
