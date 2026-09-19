"""Summarize audited native VAKRA runs without claiming an official judge score."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    grid = json.loads((args.root / "grid_manifest.json").read_bytes())
    if grid["status"] != "complete" or any(w["exit_code"] for w in grid["workers"]):
        raise ValueError("Grid incomplete")
    rows, hashes = [], {}
    manifests = sorted(args.root.glob("*/shard-*/manifest.json"))
    if len(manifests) != len(grid["workers"]):
        raise ValueError("Missing worker manifests")
    model_tasks = {}
    for path in manifests:
        manifest = json.loads(path.read_bytes())
        model = path.parent.parent.name
        cases = sorted(path.parent.glob("case-*.json"))
        episodes = [json.loads(c.read_bytes()) for c in cases]
        if [e["uuid"] for e in episodes] != manifest["selected_task_ids"]:
            raise ValueError("Case coverage or ordering mismatch")
        seen = model_tasks.setdefault(model, set())
        if seen.intersection(manifest["selected_task_ids"]):
            raise ValueError("Repeated task within model")
        seen.update(manifest["selected_task_ids"])
        for case, e in zip(cases, episodes):
            hashes[case.relative_to(args.root).as_posix()] = hashlib.sha256(case.read_bytes()).hexdigest()
            trace = e.get("trace", [])
            rows.append({"model": model, "uuid": e["uuid"], "termination": e["termination"],
                "query": e.get("query", {}).get("dialogue"), "final_answer": e.get("final_answer"),
                "usage": e.get("usage"), "elapsed_seconds": e.get("elapsed_seconds"),
                "tool_error_results": sum(bool(t.get("tool_result", {}).get("isError")) for t in trace),
                "errors": [{k:t[k] for k in ("step", "error_type", "error", "protocol_error") if k in t}
                           for t in trace if "error" in t or "protocol_error" in t],
                "max_observed_tool_text_characters": max((sum(len(c.get("text", "")) for c in
                    t.get("tool_result", {}).get("content", [])) for t in trace), default=0)})
        hashes[path.relative_to(args.root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    if len(rows) != grid["registered_episodes"]:
        raise ValueError("Registered episode coverage mismatch")
    if len({tuple(sorted(v)) for v in model_tasks.values()}) != 1:
        raise ValueError("Models evaluated different identities")
    report = {"purpose": "native-model development audit, no official evaluation score",
              "complete": True, "episodes": len(rows), "distinct_task_ids": len(next(iter(model_tasks.values()))),
              "batch_wall_seconds": grid["finished"] - grid["started"],
              "groups": [{"model": m, "episodes": sum(r["model"] == m for r in rows),
                          "agent_finished": sum(r["model"] == m and r["termination"] == "agent_finished" for r in rows),
                          "model_errors": sum(r["model"] == m and r["termination"] == "model_error" for r in rows),
                          "tool_error_results": sum(r["tool_error_results"] for r in rows if r["model"] == m)}
                         for m in sorted(model_tasks)],
              "input_sha256": hashes, "rows": rows}
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps({k:report[k] for k in ("complete", "episodes", "distinct_task_ids", "groups")}))


if __name__ == "__main__":
    main()
