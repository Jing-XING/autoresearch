"""Immutable four-worker pilot; wait for the existing five-stage queue."""
import json
import os
from pathlib import Path
import subprocess
import time
import traceback

ROOT = Path("/xingjing/autoresearch-agent-papers")
BATCH = "hotpot-pilot-v1"
REV = ROOT / "revisions" / BATCH


def main():
    output = ROOT / "runs" / BATCH
    marker = ROOT / "logs" / (BATCH + "-process.json")
    if output.exists() or marker.exists():
        raise FileExistsError("Immutable pilot already registered")
    output.mkdir(parents=True)
    registration = json.loads((REV / "protocol/registration.json").read_text())
    assert registration["registered_episodes"] == 48
    report = {"batch": BATCH, "status": "waiting_for_dependencies", "registered_episodes": 48,
              "registered": time.time(), "registration": registration, "workers": []}
    children = []

    def save():
        temporary = output / "grid_manifest.tmp"
        temporary.write_text(json.dumps(report, indent=2))
        temporary.replace(output / "grid_manifest.json")

    try:
        save()
        deadline = time.monotonic() + 36 * 3600
        while True:
            prior_path = ROOT / "logs/tau-nk-test40-v2-process.json"
            try:
                prior = json.loads(prior_path.read_text())["status"]
            except (FileNotFoundError, json.JSONDecodeError):
                prior = "pending"
            if prior == "failed":
                raise RuntimeError("Registered predecessor failed; pilot not launched")
            if prior == "complete":
                busy = subprocess.check_output(["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader"], text=True)
                if not busy.strip():
                    break
            if time.monotonic() > deadline:
                raise TimeoutError("36-hour dependency bound reached")
            time.sleep(10)
        report.update(status="running", started=time.time())
        env = dict(os.environ, PYTHONPATH=str(REV), PYTHON_DOTENV_DISABLED="1",
                   HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", OMP_NUM_THREADS="4",
                   TOKENIZERS_PARALLELISM="false", PYTHONUTF8="1")
        for gpu, (model, checkpoint, shard) in enumerate([
            ("qwen3", "Qwen3-4B-Instruct-2507", 0), ("qwen3", "Qwen3-4B-Instruct-2507", 1),
            ("qwen25", "Qwen2.5-7B-Instruct", 0), ("qwen25", "Qwen2.5-7B-Instruct", 1)]):
            command = [str(ROOT / ".venv/bin/python"), "-m", "autolab.hotpot_pilot",
                "--inputs", str(REV / "inputs/pilot.json"),
                "--selection", str(REV / "research/evidence/hotpot_snapshot_selection_v1.json"),
                "--model-path", str(ROOT / "models" / checkpoint),
                "--model-reference", str(REV / "protocol" / (model + ".json")),
                "--shard", str(shard), "--shards", "2",
                "--output", str(output / model / f"shard-{shard}")]
            with (ROOT / "logs" / f"{BATCH}-{model}-{shard}.log").open("x") as log:
                child = subprocess.Popen(command, cwd=REV, env=dict(env, CUDA_VISIBLE_DEVICES=str(gpu)),
                                         stdout=log, stderr=subprocess.STDOUT)
            row = {"model": model, "shard": shard, "gpu": gpu, "pid": child.pid,
                   "command": command, "episodes": 12, "started": time.time()}
            children.append((child, row)); report["workers"].append(row)
        save()
        deadline = time.monotonic() + 4 * 3600
        while children:
            changed = False
            for child, row in list(children):
                if child.poll() is not None:
                    row.update(exit_code=child.returncode, finished=time.time())
                    children.remove((child, row)); changed = True
                    if child.returncode:
                        raise RuntimeError("Worker failed: " + repr(row))
            if changed:
                save()
            if time.monotonic() > deadline:
                raise TimeoutError("Four-hour worker bound reached")
            if children:
                time.sleep(10)
        assert len(list(output.glob("*/shard-*/case-*.json"))) == 48
        report["status"] = "complete"
    except BaseException as exc:
        report.update(status="failed", error=str(exc), traceback=traceback.format_exc())
    finally:
        for child, row in children:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    child.kill(); child.wait()
            row.update(exit_code=child.returncode, finished=time.time())
        report["finished"] = time.time()
        save()
        with marker.open("x") as f:
            json.dump(report, f, indent=2)
    print(json.dumps({"batch": BATCH, "status": report["status"]}), flush=True)


if __name__ == "__main__":
    main()
