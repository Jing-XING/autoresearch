"""Replay only already-executed history preceding a protocol exception.

Offline hidden-state diagnosis; never repairs the invalid output or official reward.
"""
import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace


def reconstruct(native):
    from tau2.data_model.message import AssistantMessage, ToolCall, ToolMessage
    messages = []
    for item in native:
        if item["role"] == "system":
            if messages:
                raise ValueError("System message inside executed trajectory")
            continue
        if item["role"] == "assistant":
            calls = [ToolCall(id=c["id"], **c["function"]) for c in item.get("tool_calls", [])]
            messages.append(AssistantMessage(role="assistant", content=item["content"], tool_calls=calls or None))
        elif item["role"] == "tool":
            # Native logs omit error flags. The pinned strict state replayer
            # compares mutating-tool response content, not this default flag.
            messages.append(ToolMessage(role="tool", id=item["tool_call_id"],
                                        content=item["content"], requestor="assistant"))
        else:
            raise ValueError("Unexpected solo role")
    return messages


def main():
    from loguru import logger
    logger.remove()
    from autolab.tau2_native_agent import native_messages
    from autolab.tau2_native_baseline import verify_tau_source
    from autolab.tau2_prefix_audit import audit_prefixes
    from tau2.runner.helpers import get_tasks
    from tau2.data_model.simulation import SimulationRun

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--tau-repo", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    source_hash = verify_tau_source(args.tau_repo)
    tasks = {t.id: t for t in get_tasks("telecom", task_split_name="small")}
    failures, checked, hashes = [], 0, {}
    for status_path in sorted(args.root.glob("*/*/shard-*/case-*-status.json")):
        status = json.loads(status_path.read_bytes())
        audit_path = status_path.with_name(status_path.name.replace("-status", "-model-audit"))
        audit = json.loads(audit_path.read_bytes())
        events = audit["calls"]
        last = events[-1]
        native = [m for m in last["input"] if m["role"] != "system"]
        messages = reconstruct(last["input"])
        if native_messages(messages) != native:
            raise ValueError("Reconstruction does not round-trip")
        for path in (status_path, audit_path):
            hashes[path.relative_to(args.root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        if status["reward"] is not None:
            simulation_path = status_path.with_name(status_path.name.replace("-status", ""))
            simulation = SimulationRun.model_validate_json(simulation_path.read_bytes())
            if native_messages(simulation.messages[:len(messages)]) != native:
                raise ValueError("Executed prefix differs from saved official simulation")
            checked += 1
            continue
        if not last.get("protocol_error"):
            raise ValueError("Not a protocol failure; cannot assume no output execution")
        diagnostic = SimpleNamespace(task_id=status["task_id"], messages=messages,
            termination_reason=SimpleNamespace(value="protocol_exception_before_execution"),
            reward_info=SimpleNamespace(reward=None))
        result = audit_prefixes(diagnostic, tasks[status["task_id"]])
        failures.append({"status_file": status_path.relative_to(args.root).as_posix(),
                         "invalid_output_not_executed": last["reply"]["text"],
                         "last_input_sha256": last["input_sha256"], **result})
    report = {"purpose": "offline diagnosis; official exceptions remain non-success; no invalid call repaired",
              "tau_source_sha256": source_hash, "complete_simulation_prefixes_matched": checked,
              "reconstruction_limit": "Native logs omit error flags; pinned environment replay does not read those flags. Strict mutating-response checks remain enabled.",
              "input_sha256": hashes, "failures": failures}
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps({"complete_prefixes_matched": checked, "protocol_failures": len(failures),
                      "satisfied_before_exception": sum(r["final_task_satisfied"] for r in failures)}))


if __name__ == "__main__":
    main()
