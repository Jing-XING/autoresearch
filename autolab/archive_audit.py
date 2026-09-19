"""Audit archived Agent runs without executing candidates or calling any model.

The source archive is external observational evidence, not a new experiment.
Exit -9 alone does not establish timeout, and missing evaluation is not a
scientific falsification. Reports retain these distinctions and source hashes.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess

TIMEOUT = re.compile(r"(?im)^TIMEOUT after [0-9.]+\s*s\b")


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def execution_evidence(execution: dict) -> str:
    log = execution.get("exec_log", {}).get("content", "")
    if TIMEOUT.search(log):
        return "explicit_timeout"
    if execution.get("exit_code") == -9:
        return "killed_reason_unconfirmed"
    if execution.get("exit_code") not in (0, None):
        return "execution_error"
    if execution.get("eval_status") == "ran":
        if execution.get("eval_score") == 1:
            return "evaluated_pass"
        if execution.get("eval_score") is not None:
            return "evaluated_nonpass"
    return "outcome_unobserved_or_evaluator_not_run"


def embedded_integrity(obj, prefix="") -> list[dict]:
    issues = []
    if isinstance(obj, dict):
        if isinstance(obj.get("content"), str) and isinstance(obj.get("sha256"), str):
            actual = digest(obj["content"].encode("utf-8"))
            if actual != obj["sha256"]:
                issues.append({"field": prefix, "expected": obj["sha256"], "actual": actual})
        for k, v in obj.items():
            issues.extend(embedded_integrity(v, f"{prefix}.{k}" if prefix else k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            issues.extend(embedded_integrity(v, f"{prefix}[{i}]"))
    return issues


def audit(source: Path) -> dict:
    source = source.resolve()
    logs = source / "reproduction" / "section3" / "logs"
    paths = sorted((logs / "dispatches" / "solver").glob("*.json"))
    if not paths:
        raise ValueError("No solver archive records found")
    rows, integrity, manifest = [], [], []
    cells = defaultdict(list)
    seen = set()
    for path in paths:
        content = path.read_bytes()
        data = json.loads(content)
        key = (data["task_id"], data["model_dir"], data["cell"])
        if key in seen:
            raise ValueError(f"Duplicate task/model/cell: {key}")
        seen.add(key)
        rel = path.relative_to(source).as_posix()
        manifest.append({"path": rel, "sha256": digest(content)})
        integrity.extend({"source": rel, **x} for x in embedded_integrity(data))
        execution = data["execution"]
        embedded_result = execution.get("result_json", {}).get("content")
        result = json.loads(embedded_result) if embedded_result else {}
        for field in ("exit_code", "eval_status", "eval_score", "output_exists"):
            if field in result and field in execution and result[field] != execution[field]:
                integrity.append({"source": rel, "field": field, "reason": "result disagrees with index"})
        row = {
            "task_id": data["task_id"], "model": data["model_dir"], "cell": data["cell"],
            "source": rel, "evidence": execution_evidence(execution),
            "exit_code": execution.get("exit_code"), "eval_score": execution.get("eval_score"),
            "eval_status": execution.get("eval_status"),
            "solver_tokens_reported": data.get("dispatch", {}).get("tokens"),
            "solver_duration_ms": data.get("dispatch", {}).get("duration_ms"),
            "candidate_duration_seconds": result.get("cand_duration_sec"),
            "evaluator_duration_seconds": result.get("eval_duration_sec"),
        }
        rows.append(row)
        cells[(row["model"], row["cell"])].append(row)

    memory_rows = []
    for path in sorted((logs / "nk_records").glob("*.json")):
        raw = path.read_bytes()
        data = json.loads(raw)
        text = json.dumps(data).lower()
        memory_rows.append({
            "source": path.relative_to(source).as_posix(),
            "sha256": digest(raw), "task_id": data.get("task_id"),
            "timeout_lexical_mention": "timeout" in text or "timed out" in text,
            "failure": data.get("failure"),
        })
        manifest.append({"path": path.relative_to(source).as_posix(), "sha256": digest(raw)})

    baseline_pass = set()
    baseline_rows = []
    for path in sorted((logs / "baseline_results").glob("*.json")):
        raw = path.read_bytes()
        data = json.loads(raw)
        task = path.stem.removeprefix("task_")
        baseline_rows.append(task)
        if data.get("eval_score") in (1, "1"):
            baseline_pass.add(task)
        manifest.append({"path": path.relative_to(source).as_posix(), "sha256": digest(raw)})

    groups = {}
    for (model, cell), group in sorted(cells.items()):
        groups[f"{model}/{cell}"] = {
            "n": len(group),
            "evaluated_pass": sum(r["evidence"] == "evaluated_pass" for r in group),
            "evidence_counts": dict(sorted(Counter(r["evidence"] for r in group).items())),
            "reported_solver_tokens_sum": sum(r["solver_tokens_reported"] or 0 for r in group),
            "missing_solver_token_records": sum(r["solver_tokens_reported"] is None for r in group),
        }
    def passes(cell):
        return {r["task_id"] for r in cells[("sonnet_4.6", cell)]
                if r["evidence"] == "evaluated_pass"}

    cumulative = set(baseline_pass)
    cumulative_table = {"baseline": len(cumulative)}
    for label, cells_to_add in [
        ("plus_retry", ["round2_B0"]), ("plus_nkr", ["round2_NKR"]),
        ("plus_self_debug", ["round2_B2", "round3_B2"]),
        ("plus_deep_nkr", ["deepNKR_sonnet"]),
    ]:
        for cell in cells_to_add:
            cumulative |= passes(cell)
        cumulative_table[label] = len(cumulative)
    try:
        commit = subprocess.check_output(
            ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = None
    return {
        "schema": "autolab.archive_audit.v1",
        "source_url": "https://github.com/hch-wang/Negative_Knowledge",
        "source_commit": commit,
        "interpretation": "Retrospective archive audit, not independent model reruns or causal evidence.",
        "n_dispatches": len(rows), "n_unique_tasks": len({r["task_id"] for r in rows}),
        "n_baseline_tasks": len(baseline_rows),
        "evidence_counts": dict(sorted(Counter(r["evidence"] for r in rows).items())),
        "cells": groups, "cumulative_table_numerator": cumulative_table,
        "table_warning": "Cumulative union over selected attempts; not equal-budget independent method estimates.",
        "cost_warning": "Reported solver cost excludes potentially missing curation, retries, and other overhead.",
        "integrity_issues": integrity,
        "timeout_memory_mentions": [r for r in memory_rows if r["timeout_lexical_mention"]],
        "memory_warning": "Lexical timeout mentions are not verified causal diagnoses or erroneous labels.",
        "records": rows, "source_manifest": manifest,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in [
        "source_commit", "n_dispatches", "n_unique_tasks", "n_baseline_tasks",
        "evidence_counts", "cumulative_table_numerator",
    ]}, indent=2))
    print(f"Integrity issues: {len(report['integrity_issues'])}")
    print(f"Report: {args.output}")
    return 1 if report["integrity_issues"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
