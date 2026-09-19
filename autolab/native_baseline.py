"""Fixed development baseline using the checkpoint's native function-call template."""
import argparse
import importlib.metadata
import json
from pathlib import Path

from autolab.local_smoke import sha256_file
from autolab.memory_pilot import SQLTask
from autolab.native_tool_agent import NativeTransformersModel, SQL_TOOLS, run_native_episode
from autolab.tool_agent import Budget, write_episode


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model-path", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    metadata = {"purpose": "development_baseline_only", "model_path": str(args.model_path),
                "decoder": "greedy_native_tool_template", "seed": 20260919,
                "packages": {n: importlib.metadata.version(n) for n in ["torch", "transformers", "accelerate"]},
                "source_sha256": {n: sha256_file(Path(__file__).parent / n) for n in
                                  ["native_tool_agent.py", "native_baseline.py", "local_smoke.py", "memory_pilot.py"]},
                "tokenizer_config_sha256": sha256_file(args.model_path / "tokenizer_config.json")}
    write_episode(metadata, args.output, "manifest")
    model = NativeTransformersModel(args.model_path)
    rows = []
    for case in range(12):
        env = SQLTask(9000 + case, case)
        result = run_native_episode(model, env, env.task, Budget(10, 7, 384),
                                    {**metadata, "case": case, "condition": "none"}, SQL_TOOLS)
        write_episode(result, args.output, f"case-{case:02d}")
        env.db.close()
        row = {"case": case, "success": result["evaluation"]["success"],
               "termination": result["termination"], "usage": result["usage"],
               "protocol_errors": sum("protocol_error" in t for t in result["trace"])}
        rows.append(row)
        print(json.dumps(row), flush=True)
    write_episode({"purpose": "development_only", "n": len(rows),
                   "successes": sum(r["success"] for r in rows), "rows": rows}, args.output, "summary")
    print("NATIVE_BASELINE_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
