"""Immutable two-worker structural pilot; wait for the complete existing queue."""
import json
import os
from pathlib import Path
import subprocess
import time
import traceback

ROOT = Path("/xingjing/autoresearch-agent-papers")
BATCH = "research-unit-pilot-v1"
REV = ROOT / "revisions" / BATCH


def main():
    output = ROOT / "runs" / BATCH
    marker = ROOT / "logs" / (BATCH + "-process.json")
    if output.exists() or marker.exists():
        raise FileExistsError("Immutable pilot already registered")
    output.mkdir(parents=True)
    registration = json.loads((REV / "protocol/registration.json").read_text())
    assert registration["registered_episodes"] == 30
    report = {"batch": BATCH, "status": "waiting_for_dependencies", "registered_episodes": 30,
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
            prior_path = ROOT / "logs/hotpot-pilot-v1-process.json"
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
        for gpu, model, checkpoint in [
            (0, "qwen3", "Qwen3-4B-Instruct-2507"),
            (2, "qwen25", "Qwen2.5-7B-Instruct")]:
            command = [str(ROOT / ".venv/bin/python"), "-m", "autolab.research_unit_pilot",
                "--inputs", str(REV / "inputs/pilot.json"),
                "--registration", str(REV / "protocol/registration.json"),
                "--model-path", str(ROOT / "models" / checkpoint),
                "--model-reference", str(REV / "protocol" / (model + ".json")),
                "--output", str(output / model)]
            with (ROOT / "logs" / f"{BATCH}-{model}.log").open("x") as log:
                child = subprocess.Popen(command, cwd=REV, env=dict(env, CUDA_VISIBLE_DEVICES=str(gpu)),
                                         stdout=log, stderr=subprocess.STDOUT)
            row = {"model": model, "gpu": gpu, "pid": child.pid,
                   "command": command, "episodes": 15, "started": time.time()}
            children.append((child, row)); report["workers"].append(row)
        save()
        deadline = time.monotonic() + 2 * 3600
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
                raise TimeoutError("Two-hour worker bound reached")
            if children:
                time.sleep(10)
        assert len(list(output.glob("*/case-*.json"))) == 30
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
