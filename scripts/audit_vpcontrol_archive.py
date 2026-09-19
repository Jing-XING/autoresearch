"""Independently aggregate frozen VP-CONTROL records; never execute archive code.

This checks materialized table arithmetic, not model generations or simulator
correctness. Conditional unsafe risk uses executed actions as its denominator;
the paper's risk uses every task. Both are retained without relabelling either.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import zipfile

ARCHIVE_SHA = "d96621f7dae9467312d8edf6b0a6bdc9ef711149499e4c2ebcc7fa3a3e4c9be1"
PREFIX = "vpcontrol/artifacts/stage2/main/"


def audit(archive: Path) -> dict:
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != ARCHIVE_SHA:
        raise ValueError("Archive does not match the frozen author release")
    aggregates = defaultdict(Counter)
    clusters = defaultdict(set)
    cluster_splits = defaultdict(set)
    identifiers = set()
    split_rows = Counter()
    violations = []
    metrics = {
        "unsafe_rate": "unsafe", "coverage": "coverage",
        "safe_task_success": "safe_task_success", "execute_rate": "executed",
        "verification_cost": "verification_cost", "escalation_cost": "escalation_cost",
        "total_cost": "cost", "defer_rate": "defer", "block_rate": "block",
    }
    with zipfile.ZipFile(archive) as z:
        table = json.loads(z.read(PREFIX + "strategy_table.json"))
        info = json.loads(z.read(PREFIX + "run_info.json"))
        policies = json.loads(z.read(PREFIX + "fitted_policies.json"))
        hashes = {n: hashlib.sha256(z.read(PREFIX + n)).hexdigest() for n in
                  ("strategy_table.json", "run_info.json", "fitted_policies.json")}
        row_hash = hashlib.sha256()
        plan_count = 0
        with z.open(PREFIX + "replay_rows.jsonl") as f:
            for raw in f:
                row_hash.update(raw)
                if not raw.strip():
                    continue
                row = json.loads(raw)
                identity = (row["scenario_id"], row["actor"], row["seed"])
                if identity in identifiers:
                    raise ValueError(f"Duplicate row: {identity}")
                identifiers.add(identity)
                split = row["split"]
                split_rows[split] += 1
                cluster_splits[row["cluster"]].add(split)
                for plan, record in row["plan_results"].items():
                    plan_count += 1
                    if record["unsafe"] and not record["executed"]:
                        violations.append([list(identity), plan, "unsafe without execution"])
                    if abs(record["cost"] - record["verification_cost"] - record["escalation_cost"]) > 1e-10:
                        violations.append([list(identity), plan, "cost components"])
                if set(row["policy_plans"]) != set(table):
                    raise ValueError("Policy coverage changed between records and table")
                for strategy, plan in row["policy_plans"].items():
                    record = row["plan_results"][plan]
                    key = (strategy, split)
                    a = aggregates[key]
                    a["n"] += 1
                    clusters[key].add(row["cluster"])
                    for field in set(metrics.values()) - {"defer", "block"}:
                        a[field] += record[field]
                    a["defer"] += record["final"] == "defer"
                    a["block"] += record["final"] == "block"
        hashes["replay_rows.jsonl"] = row_hash.hexdigest()
    if len(identifiers) != info["rows"] or any(split_rows[k] != info[k] for k in split_rows):
        raise ValueError("Manifest row counts disagree")
    if any(len(v) != 1 for v in cluster_splits.values()):
        raise ValueError("Template crosses train/calibration/test split")
    diffs = []
    summaries = {}
    for (strategy, split), a in sorted(aggregates.items()):
        frozen = table[strategy][split]
        got = {name: a[field] / a["n"] for name, field in metrics.items()}
        got.update(n=a["n"], clusters=len(clusters[strategy, split]), unsafe_count=a["unsafe"])
        for field, value in got.items():
            if abs(frozen[field] - value) > 1e-10:
                diffs.append({"strategy": strategy, "split": split, "metric": field,
                              "frozen": frozen[field], "recomputed": value})
        got["executed_count"] = a["executed"]
        got["unsafe_given_execution"] = a["unsafe"] / a["executed"] if a["executed"] else None
        summaries.setdefault(strategy, {})[split] = got
    return {
        "source": "https://doi.org/10.6084/m9.figshare.33511441.v1",
        "archive_sha256": digest, "member_sha256": hashes,
        "scope": "Independent arithmetic of author-materialized main-stage records only; no model calls or simulator replay",
        "rows": len(identifiers), "split_rows": dict(split_rows),
        "independent_template_counts": dict(Counter(next(iter(v)) for v in cluster_splits.values())),
        "plan_records_consistency_checked": plan_count,
        "table_cells_checked": len(aggregates) * (len(metrics) + 3),
        "internal_violations": violations, "table_mismatches": diffs,
        "arithmetic_passed": not violations and not diffs,
        "risk_denominators": {"unsafe_rate": "all task proposals", "unsafe_given_execution": "executed proposals; null when zero executed"},
        "strategies": summaries,
        "fitted_policy_keys": list(policies),
        "limitations": ["Frozen public data; this is not a new held-out experiment",
                        "Does not verify raw LLM verdicts, simulator semantics, confidence intervals or calibration validity",
                        "Different risk denominators answer different questions; neither is substituted for the author's estimand"],
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    result = audit(a.archive)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")
    print(json.dumps({k: result[k] for k in ("rows", "split_rows", "independent_template_counts", "plan_records_consistency_checked", "table_cells_checked", "arithmetic_passed")}))
    for name in ("always_execute", "cross_model_same_source_vote", "always_independent_source", "always_exact_guard", "portfolio@0.01", "portfolio@0.02", "portfolio@0.05"):
        print(name, json.dumps(result["strategies"][name]["test"]))
    if not result["arithmetic_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
