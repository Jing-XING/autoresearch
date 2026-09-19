"""Validate matched development coverage; report execution, not answer scores."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    grid = json.loads((args.root / "grid_manifest.json").read_bytes())
    if grid["status"] != "complete" or len(grid["workers"]) != 4 or any(w["exit_code"] for w in grid["workers"]):
        raise ValueError("Incomplete worker grid")
    expected = {(c,m) for c in ("original", "coverage_check") for m in ("qwen3", "qwen25")}
    if {(w["condition"],w["model"]) for w in grid["workers"]} != expected:
        raise ValueError("Unexpected worker allocation")
    rows, hashes, groups, manifests, records = [], {}, [], {}, {}
    for condition, model in sorted(expected):
        folder = args.root / condition / model / "shard-0"
        manifest_path = folder / "manifest.json"
        m = json.loads(manifest_path.read_bytes())
        if (m["instruction_condition"], m["max_steps"], m["max_new_tokens"], m["max_input_tokens"]) != (condition,20,512,32768):
            raise ValueError("Unexpected protocol")
        cases = sorted(folder.glob("case-*.json"))
        episodes = [json.loads(f.read_bytes()) for f in cases]
        if len(episodes) != 12 or [e["uuid"] for e in episodes] != m["selected_task_ids"]:
            raise ValueError("Task coverage/order mismatch")
        manifests[(condition,model)] = m
        hashes[manifest_path.relative_to(args.root).as_posix()] = digest(manifest_path)
        for path, e in zip(cases, episodes):
            records[(condition,model,e["uuid"])] = e
            if e.get("instruction_condition", condition) != condition:
                raise ValueError("Episode condition mismatch")
            hashes[path.relative_to(args.root).as_posix()] = digest(path)
            trace = e.get("trace", [])
            if trace and not trace[0]["input"][0]["content"].endswith(m["instruction_suffix"]):
                raise ValueError("Recorded prompt differs from declared suffix")
            rows.append({"condition": condition, "model": model, "uuid": e["uuid"],
                "source": path.relative_to(args.root).as_posix(), "query": e.get("query", {}).get("dialogue"),
                "termination": e["termination"], "final_answer": e.get("final_answer"),
                "usage": e.get("usage", {}),
                "tool_error_results": sum(bool(t.get("tool_result", {}).get("isError")) for t in trace),
                "validation_error_payloads": sum(any(
                    x.get("text", "").startswith("Input validation error:")
                    for x in t.get("tool_result", {}).get("content", [])) for t in trace),
                "errors": [{k:t[k] for k in ("step", "error_type", "error", "protocol_error") if k in t}
                           for t in trace if "error" in t or "protocol_error" in t]})
        selected = [r for r in rows if (r["condition"],r["model"]) == (condition,model)]
        groups.append({"condition": condition, "model": model, "n": len(selected),
                       "terminations": dict(Counter(r["termination"] for r in selected)),
                       "tool_error_results": sum(r["tool_error_results"] for r in selected),
                       "validation_error_payloads": sum(r["validation_error_payloads"] for r in selected),
                       "usage": {k:sum(r["usage"].get(k,0) for r in selected) for k in
                                 ("model_calls", "tool_calls", "input_tokens", "output_tokens", "generation_seconds", "protocol_errors")}})
    common = ("selected_task_ids", "all_task_ids", "preparation_sha256", "queries_sha256",
              "agent_prompt_source_sha256", "source_sha256", "packages", "seed", "decoder", "supplied_prefix")
    first = next(iter(manifests.values()))
    for m in manifests.values():
        if any(m[k] != first[k] for k in common):
            raise ValueError("Matched conditions have unequal tasks/runtime")
    for model in ("qwen3", "qwen25"):
        a,b = (manifests[(c,model)] for c in ("original", "coverage_check"))
        if a["model_files_sha256"] != b["model_files_sha256"]:
            raise ValueError("Checkpoint mismatch")
        if a["instruction_suffix"] != "" or not b["instruction_suffix"]:
            raise ValueError("Instruction-control definition missing")
        for uuid in a["selected_task_ids"]:
            original = records[("original",model,uuid)]
            coverage = records[("coverage_check",model,uuid)]
            if original.get("trace") and coverage.get("trace"):
                oi,ci = original["trace"][0]["input"],coverage["trace"][0]["input"]
                if ci[0]["content"] != oi[0]["content"] + b["instruction_suffix"] or ci[1:] != oi[1:]:
                    raise ValueError("Actual prompt/query control mismatch")
                if original["tools"] != coverage["tools"] or original["initial_peek"] != coverage["initial_peek"]:
                    raise ValueError("Actual tool schema/initial observation mismatch")
    if len(rows) != grid["registered_episodes"]:
        raise ValueError("Registered count mismatch")
    report = {"purpose": "development execution audit; no answer correctness score",
              "error_field_definition": "tool_error_results counts MCP isError=true only; validation_error_payloads independently counts explicit validation-error text, including isError=false payloads. These counts can overlap and must not be added.",
              "complete": True, "episodes":len(rows), "distinct_task_ids":12,
              "batch_wall_seconds":grid["finished"]-grid["started"], "groups":groups,
              "input_sha256":hashes, "rows":rows}
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(report,f,ensure_ascii=False,indent=2)
    print(json.dumps({"complete":True,"groups":groups}))


if __name__ == "__main__":
    main()
