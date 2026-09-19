"""Create policy-invariant offline cutoffs from recorded solo trajectories.

Only observed messages and stop metadata enter inputs/. Future outcomes live in
labels/ for evaluator use. This is development data preparation, not evidence
that a particular reflection or memory intervention improves an agent.
"""
import argparse
import hashlib
import json
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def visible_prefix(messages, cutoff):
    if cutoff < 1:
        raise ValueError("Cutoff must be positive")
    result, pos, generation = [], 0, 0
    while pos < len(messages) and generation < cutoff:
        message = messages[pos]
        if message["role"] != "assistant":
            raise ValueError("Expected solo assistant message")
        calls = message.get("tool_calls") or []
        end = pos + 1 + len(calls)
        if end > len(messages):
            raise ValueError("Incomplete tool-result group")
        assistant = {"role": "assistant", "content": message.get("content") or ""}
        if calls:
            assistant["tool_calls"] = [
                {"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": c["arguments"]}}
                for c in calls
            ]
        result.append(assistant)
        for offset, call in enumerate(calls):
            response = messages[pos + 1 + offset]
            if response["role"] != "tool" or response["id"] != call["id"]:
                raise ValueError("Tool-result identity mismatch")
            result.append({"role": "tool", "tool_call_id": response["id"], "content": response.get("content") or ""})
        pos, generation = end, generation + 1
    return result, generation, pos == len(messages)


def make_record(simulation, audit, cutoff):
    if simulation["task_id"] != audit["task_id"]:
        raise ValueError("Task identity mismatch")
    observed, steps, reaches_recorded_end = visible_prefix(simulation["messages"], cutoff)
    initial = audit["calls"][0]["input"]
    if any(m["role"] != "system" for m in initial):
        raise ValueError("Expected policy/ticket-only initial solo input")
    stop_reason = simulation["termination_reason"] if reaches_recorded_end else "external_generation_cutoff"
    observed_reward = simulation["reward_info"]["reward"] if reaches_recorded_end else 0.0
    payload = {"system_messages": initial, "observed_messages": observed,
               "generation_budget": cutoff, "observed_generations": steps,
               "stop_reason": stop_reason, "observed_benchmark_reward": observed_reward}
    # These labels are never included in the curator-visible payload.
    label = {"task_id": simulation["task_id"], "recorded_full_reward": simulation["reward_info"]["reward"],
             "recorded_full_termination": simulation["termination_reason"],
             "unobserved_continuation_exists": not reaches_recorded_end,
             "later_recorded_success": not reaches_recorded_end and simulation["reward_info"]["reward"] == 1.0,
             "continuation_beyond_recorded_horizon": "not observed"}
    return payload, label


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cutoffs", type=int, nargs="+", default=[4, 8, 16])
    args = parser.parse_args()
    if len(set(args.cutoffs)) != len(args.cutoffs) or min(args.cutoffs) < 1:
        parser.error("Unique positive cutoffs required")
    args.output.mkdir(parents=True, exist_ok=False)
    for name in ("inputs", "labels"):
        (args.output / name).mkdir()
    rows, excluded = [], []
    for status_path in sorted(args.root.glob("*/shard-*/case-*-status.json")):
        status = json.loads(status_path.read_bytes())
        identity = status_path.relative_to(args.root).as_posix()
        if status["reward"] is None:
            excluded.append({"file": identity, "reason": "no complete recorded simulation", "task_id": status["task_id"]})
            continue
        sim_path = status_path.with_name(status_path.name.replace("-status", ""))
        audit_path = status_path.with_name(status_path.name.replace("-status", "-model-audit"))
        sim, audit = json.loads(sim_path.read_bytes()), json.loads(audit_path.read_bytes())
        for cutoff in args.cutoffs:
            payload, label = make_record(sim, audit, cutoff)
            record_id = digest({"source": identity, "cutoff": cutoff})[:24]
            for folder, data in (("inputs", payload), ("labels", label)):
                (args.output / folder / (record_id + ".json")).write_text(json.dumps(data, indent=2), encoding="utf-8")
            rows.append({"record_id": record_id, "model": status_path.parent.parent.name,
                         "cluster_id": sim["task_id"], "source": identity, "cutoff": cutoff,
                         "payload_sha256": digest(payload), "label_sha256": digest(label),
                         "simulation_sha256": hashlib.sha256(sim_path.read_bytes()).hexdigest(),
                         "model_audit_sha256": hashlib.sha256(audit_path.read_bytes()).hexdigest()})
    manifest = {"purpose": "development only; correlated prefixes are not independent tasks",
                "intervention": "offline external generation cutoff; source policy input unchanged",
                "evaluation_warning": "Later success does not imply every prefix action was correct, and cannot establish memory utility",
                "cutoffs": args.cutoffs, "records": rows, "excluded": excluded}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"records": len(rows), "excluded_runs": len(excluded)}))


if __name__ == "__main__":
    main()
