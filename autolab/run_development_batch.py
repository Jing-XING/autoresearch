"""Bounded four-GPU development screening, gated by an infrastructure smoke test."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parents[2]
    repo = root / "repo"
    weights = root / "models/Qwen3-4B-Instruct-2507"
    smoke = root / "runs/smoke"
    output = root / "runs/memory-pilot-v1"
    output.mkdir(parents=True, exist_ok=False)
    def execute(module, arguments, gpu, label, timeout):
        env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(gpu), OMP_NUM_THREADS="4",
                   TOKENIZERS_PARALLELISM="false", HF_HUB_OFFLINE="1")
        with (root / "logs" / f"{label}.log").open("x") as log:
            try:
                result = subprocess.run([sys.executable, "-u", "-m", module,
                                         "--model-path", str(weights), *arguments],
                                        cwd=repo, env=env, stdout=log, stderr=subprocess.STDOUT,
                                        timeout=timeout)
                return {"label": label, "exit_code": result.returncode}
            except subprocess.TimeoutExpired:
                return {"label": label, "timeout": True}
    checked = execute("autolab.local_smoke", ["--output", str(smoke), "--run-prefix", "qwen3-4b-smoke-v2"],
                      0, "agent-smoke-v2", 600)
    print(json.dumps(checked), flush=True)
    if checked.get("exit_code") != 0:
        raise RuntimeError("Smoke process failed; no pilot started")
    limited = json.loads((smoke / "qwen3-4b-smoke-v2-limited.json").read_text())
    sufficient = json.loads((smoke / "qwen3-4b-smoke-v2-sufficient.json").read_text())
    if limited["evaluation"]["success"] is not False or sufficient["evaluation"]["success"] is not True:
        raise RuntimeError("Smoke expectations failed; inspect artifacts before pilot")
    print("SMOKE_GATE_PASSED", flush=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(execute, "autolab.memory_pilot",
                               ["--output", str(output), "--shard", str(i), "--shards", "4"],
                               i, f"memory-pilot-v1-shard-{i}", 1800) for i in range(4)]
        results = [f.result() for f in futures]
    (output / "process_results.json").write_text(json.dumps(results, indent=2))
    print("DEVELOPMENT_BATCH_STOPPED", json.dumps(results), flush=True)


if __name__ == "__main__":
    main()
