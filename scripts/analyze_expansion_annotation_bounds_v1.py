"""Post-hoc label sensitivity, distinct from task resampling or adjudication."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autolab.vakra_review_summary import summarize_review


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check(value, message):
    if not value:
        raise ValueError(message)


def label_groups(rows):
    """A semantic judgment is shared only for exact text under the same task."""
    groups = {}
    for row in rows:
        if row["final_answer"] is None:
            check(row["answer_label"] in ("no_answer", "ambiguous"), "Absent response has a value label")
            continue
        check(row["termination"] == "agent_finished", "Unexpected present final outside terminal answer path")
        task = (row["domain"], row["uuid"])
        key = task + (row["final_answer"],)
        if key not in groups:
            groups[key] = {"domain": task[0], "uuid": task[1], "task_index": row["task_index"],
                "answer_sha256": sha(row["final_answer"].encode()),
                "group_id": sha(json.dumps(key, ensure_ascii=False, separators=(",", ":")).encode()),
                "label": row["answer_label"], "sources": []}
        group = groups[key]
        check(group["label"] == row["answer_label"], "Identical task/answer text has conflicting labels: " + group["group_id"])
        check(group["label"] in ("correct", "incorrect", "ambiguous"), "Invalid present-response label")
        group["sources"].append({k: row[k] for k in ("model", "condition", "source", "source_sha256")})
    return sorted(groups.values(), key=lambda g: g["group_id"])


def change_envelope(delta, effects, max_changes):
    """Exact extrema of an additive contrast after at most k group flips."""
    check(all(e["delta_change"] in (-1, 1) for e in effects), "Expected unit paired-label effects")
    down = sorted((e for e in effects if e["delta_change"] < 0), key=lambda e: (e["delta_change"], e["group_id"]))
    up = sorted((e for e in effects if e["delta_change"] > 0), key=lambda e: (-e["delta_change"], e["group_id"]))
    curve = [{"maximum_changed_judgments": k,
              "minimum_net_difference": delta + sum(e["delta_change"] for e in down[:k]),
              "maximum_net_difference": delta + sum(e["delta_change"] for e in up[:k])}
             for k in range(max_changes + 1)]
    toward = down if delta > 0 else up
    total, tie, reversal = delta, None, None
    if delta == 0:
        tie = {"changed_judgments": 0, "groups": []}
    for k, effect in enumerate(toward, 1):
        total += effect["delta_change"]
        if tie is None and total == 0:
            tie = {"changed_judgments": k, "groups": toward[:k]}
        if delta * total < 0:
            reversal = {"changed_judgments": k, "groups": toward[:k]}
            break
    return {"curve": curve, "to_exact_tie": tie, "to_strictly_reverse_observed_sign": reversal,
            "decreasing_judgments_available": len(down), "increasing_judgments_available": len(up)}


def analyze_rows(rows):
    groups = label_groups(rows)
    models = sorted({r["model"] for r in rows})
    result = {}
    for model in models:
        pool = [r for r in rows if r["model"] == model]
        by_task = defaultdict(dict)
        for row in pool:
            key = row["domain"], row["uuid"]
            check(row["condition"] not in by_task[key], "Duplicate prompt result")
            by_task[key][row["condition"]] = row
        check(all(set(p) == {"original", "coverage_check"} for p in by_task.values()), "Incomplete prompt pair")
        delta, scored, ambiguous = 0, 0, []
        for (domain, uid), pair in sorted(by_task.items()):
            a, b = pair["original"], pair["coverage_check"]
            check((a["answer_label"] == "ambiguous") == (b["answer_label"] == "ambiguous"), "Changed ambiguity mask")
            if a["answer_label"] != "ambiguous":
                scored += 1
                delta += int(b["answer_label"] == "correct") - int(a["answer_label"] == "correct")
                continue
            if a["final_answer"] == b["final_answer"]:
                lo = hi = 0
                reason = "both_absent" if a["final_answer"] is None else "identical_final_text"
            else:
                lo = -int(a["final_answer"] is not None)
                hi = int(b["final_answer"] is not None)
                reason = "different_final_text_or_one_absent"
            ambiguous.append({"domain": domain, "uuid": uid, "delta_bounds": [lo, hi], "reason": reason})
        effects = []
        for group in groups:
            if group["label"] == "ambiguous":
                continue
            weight = sum((1 if r["condition"] == "coverage_check" else -1)
                         for r in group["sources"] if r["model"] == model)
            if weight:
                effects.append({"group_id": group["group_id"], "old_label": group["label"],
                    "delta_change": weight * (1 - 2 * int(group["label"] == "correct"))})
        low = delta + sum(r["delta_bounds"][0] for r in ambiguous)
        high = delta + sum(r["delta_bounds"][1] for r in ambiguous)
        result[model] = {"scored_tasks": scored, "ambiguous_tasks": len(ambiguous), "observed_net_difference": delta,
            "annotation_flip_sensitivity": change_envelope(delta, effects, 5),
            "all_task_label_relaxation": {"tasks": len(by_task), "net_difference_bounds": [low, high],
                "percentage_point_bounds": [100 * low / len(by_task), 100 * high / len(by_task)],
                "ambiguous_pairs": ambiguous}}
    return {"models": result, "groups": groups,
        "exact_text_consistency": {"present_executions": sum(r["final_answer"] is not None for r in rows),
            "distinct_task_text_judgments": len(groups), "repeated_judgment_groups": sum(len(g["sources"]) > 1 for g in groups),
            "executions_in_repeated_groups": sum(len(g["sources"]) for g in groups if len(g["sources"]) > 1),
            "conflicting_label_groups": 0}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    ev = ROOT / "research/evidence"
    paths = {"summary": ev / "vakra_expansion_complete_grid_v1.json",
             "annotations": ev / "vakra_expansion_complete_annotations_v1.json",
             "cards": ev / "vakra_domain_expansion_sql_cards_v1.json",
             "review": ev / "vakra_expansion_complete_answer_summary_v1.json"}
    summary, ann, cards, review = [json.loads(paths[k].read_bytes()) for k in ("summary", "annotations", "cards", "review")]
    check(ann["execution_summary_sha256"] == sha(paths["summary"].read_bytes()) == review["execution_summary_sha256"], "Execution evidence changed")
    check(review["annotations_sha256"] == sha(paths["annotations"].read_bytes()), "Annotations changed")
    check(ann["audit_cards_sha256"] == sha(paths["cards"].read_bytes()) == review["audit_cards_sha256"], "Frozen interpretations changed")
    checked = summarize_review(summary, ann, cards["cards"])
    check(checked["groups"] == review["groups"] and checked["paired"] == review["paired"], "Primary review recomputation differs")
    labels = {(r["domain"], r["uuid"], r["model"], r["condition"]): r for r in ann["rows"]}
    archive = ROOT / "results/remote/vakra-expansion-v2-complete.zip"
    check(sha(archive.read_bytes()) == "2e59af3255513bea2933f61822ad39131fb33f8de59ad5b1b5b2e10be7c572f5", "Raw archive changed")
    rows = []
    with zipfile.ZipFile(archive) as z:
        check(len(z.namelist()) == len(set(z.namelist())) == 517, "Raw inventory mismatch")
        for row in summary["rows"]:
            data = z.read("runs/vakra-expansion-v2/" + row["source"])
            check(sha(data) == summary["input_sha256"][row["source"]], "Raw episode differs")
            raw = json.loads(data)
            check(raw["final_answer"] == row["final_answer"] and raw["termination"] == row["termination"], "Summary response differs from actual record")
            label = labels[tuple(row[k] for k in ("domain", "uuid", "model", "condition"))]
            rows.append(dict(row, answer_label=label["answer_label"], source_sha256=label["source_sha256"]))
    check(len(rows) == 420, "Incomplete registered grid")
    report = analyze_rows(rows)
    check(all(r["scored_tasks"] == 49 and r["ambiguous_tasks"] == 21 for r in report["models"].values()), "Wrong denominator")
    report.update(purpose=__doc__, raw_archive_sha256=sha(archive.read_bytes()),
        evidence_sha256={p.name: sha(p.read_bytes()) for p in paths.values()},
        script_sha256=sha(Path(__file__).read_bytes()),
        limits=["Post-outcome sensitivity, not a preregistered test, new method or independent adjudication.",
            "A changed judgment flips all exact task/text occurrences together, including other checkpoints; per-model extrema are not necessarily jointly attainable.",
            "Missing finals stay unsuccessful; exact text matching does not establish semantic equivalence for different strings.",
            "Flip witnesses are hypothetical errors, not discovered mistakes or estimates of annotator error probability.",
            "Ambiguity envelopes hold the 49 scored tasks fixed and relax binary labels on 21 ambiguous tasks, subject only to exact-text equality and absent-answer constraints.",
            "These are conservative label-assignment envelopes, not sharp bounds over coherent SQL interpretations, population confidence intervals or changes to the primary score."])
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps({"consistency": report["exact_text_consistency"], "models": {m: {
        "net_difference": r["observed_net_difference"], "tie": r["annotation_flip_sensitivity"]["to_exact_tie"],
        "reverse": r["annotation_flip_sensitivity"]["to_strictly_reverse_observed_sign"],
        "all_task_bounds": r["all_task_label_relaxation"]["net_difference_bounds"]} for m, r in report["models"].items()}}))


if __name__ == "__main__":
    main()
