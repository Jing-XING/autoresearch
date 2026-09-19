"""Read-only completeness audit of official tau2-bench archived simulations."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess


def audit(source: Path) -> dict:
    files = sorted((source / "data/tau2/results/final").glob("*.json"))
    if not files:
        raise ValueError("No official final result JSON files found")
    reports = []
    for path in files:
        raw = path.read_bytes()
        data = json.loads(raw)
        info = data["info"]
        tasks = {str(t["id"]) for t in data["tasks"]}
        trials = info["num_trials"]
        expected = {(task, trial) for task in tasks for trial in range(trials)}
        sims = data["simulations"]
        keys = [(str(s["task_id"]), s["trial"]) for s in sims]
        duplicates = [key for key, count in Counter(keys).items() if count > 1]
        missing = sorted(expected - set(keys))
        unexpected = sorted(set(keys) - expected)
        rewards = [(s.get("reward_info") or {}).get("reward") for s in sims]
        cap_sims = [s for s in sims if s.get("termination_reason") == "max_steps"]
        observed = [r for r in rewards if r is not None]
        capped_rewards = [(s.get("reward_info") or {}).get("reward") for s in cap_sims]
        reports.append({
            "file": path.name, "sha256": hashlib.sha256(raw).hexdigest(),
            "recorded_execution_commit": info.get("git_commit"),
            "agent": info["agent_info"]["llm"],
            "agent_implementation": info["agent_info"]["implementation"],
            "agent_args": info["agent_info"].get("llm_args"),
            "user": info["user_info"]["llm"],
            "user_implementation": info["user_info"]["implementation"],
            "domain": info["environment_info"]["domain_name"],
            "max_steps": info["max_steps"], "num_trials": trials,
            "n_tasks": len(tasks), "n_runs": len(sims),
            "missing_task_trials": missing, "duplicate_task_trials": duplicates,
            "unexpected_task_trials": unexpected,
            "termination_counts": dict(sorted(Counter(s.get("termination_reason") for s in sims).items())),
            "missing_reward": len(rewards) - len(observed),
            "pass_count": sum(r == 1 for r in rewards),
            "cap_count": len(cap_sims), "cap_with_observed_reward": sum(r is not None for r in capped_rewards),
            "cap_pass_count": sum(r == 1 for r in capped_rewards),
            "missing_duration": sum(s.get("duration") is None for s in sims),
            "missing_agent_cost": sum(s.get("agent_cost") is None for s in sims),
            "missing_user_cost": sum(s.get("user_cost") is None for s in sims),
            "missing_agent_usage_messages": sum(
                m.get("usage") is None for s in sims for m in s.get("messages", [])
                if m.get("role") == "assistant"
            ),
        })
    integrity = [
        r["file"] for r in reports if
        r["missing_task_trials"] or r["duplicate_task_trials"] or r["unexpected_task_trials"]
    ]
    commit = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
    ).strip()
    return {
        "schema": "autolab.tau2_archive_audit.v1",
        "source_url": "https://github.com/sierra-research/tau2-bench",
        "source_commit": commit, "source_license": "MIT",
        "files": reports,
        "summary": {
            "n_files": len(reports), "n_runs": sum(r["n_runs"] for r in reports),
            "missing_rewards": sum(r["missing_reward"] for r in reports),
            "capped_runs": sum(r["cap_count"] for r in reports),
            "capped_observed_rewards": sum(r["cap_with_observed_reward"] for r in reports),
            "capped_passes": sum(r["cap_pass_count"] for r in reports),
            "files_with_incomplete_or_duplicate_design": integrity,
        },
        "interpretation": [
            "These are archived author runs, not experiments newly executed in this project.",
            "Max-step termination is not a missing outcome when the evaluator supplied a reward.",
            "Task lists support within-file completeness only; unreported upstream runs remain unknown.",
            "Different agent/user/environment settings and commits must not be pooled as an equal-conditions comparison.",
            "No state evaluation at intermediate prefixes is inferred from final reward.",
        ],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    report = audit(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
