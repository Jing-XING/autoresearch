"""Freeze disjoint pilot/evaluation inputs without exposing reference answers."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = "hotpot-snapshot-isolation-20260919-v1:"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    data_path = ROOT / "results/third_party/hotpotqa-control/hotpot_dev_distractor_v1.json"
    manifest_path = ROOT / "research/evidence/hotpot_control_data_manifest_v1.json"
    manifest = json.loads(manifest_path.read_bytes())
    assert sha(data_path) == manifest["dataset_sha256"]
    data = json.loads(data_path.read_bytes())
    archive_path = ROOT / "research/evidence/speculative_action_trajectory_audit_v1.json"
    archive = json.loads(archive_path.read_bytes())
    excluded = set().union(*map(set, archive["folder_question_hashes"].values()))
    assert len(excluded) == 94
    question_hash = lambda r: hashlib.sha256(r["question"].strip().encode()).hexdigest()
    matched = [r["_id"] for r in data if question_hash(r) in excluded]
    eligible = [r for r in data if question_hash(r) not in excluded]
    ordered = sorted(eligible, key=lambda r: hashlib.sha256((SEED + r["_id"]).encode()).hexdigest())
    out = ROOT / "results/preparations/hotpot-snapshot-control-v1"
    out.mkdir(parents=True, exist_ok=False)
    groups = {}
    for name, rows in [("pilot", ordered[:8]), ("evaluation", ordered[8:48])]:
        public = [{"id": r["_id"], "question": r["question"], "context": r["context"]} for r in rows]
        gold = [{"_id": r["_id"], "answer": r["answer"], "supporting_facts": r["supporting_facts"]} for r in rows]
        for suffix, items in [("inputs", public), ("gold", gold)]:
            (out / f"{name}.{suffix}.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
        assert all(set(r) == {"id", "question", "context"} for r in public)
        groups[name] = {"ids": [r["_id"] for r in rows], "inputs_sha256": sha(out / f"{name}.inputs.json"),
                        "gold_sha256": sha(out / f"{name}.gold.json"), "tasks": len(rows)}
    assert not set(groups["pilot"]["ids"]) & set(groups["evaluation"]["ids"])
    report = {"purpose": __doc__, "seed": SEED, "source_manifest_sha256": sha(manifest_path),
              "dataset_sha256": sha(data_path), "archive_audit_sha256": sha(archive_path),
              "archive_question_hashes_excluded": sorted(excluded), "matching_dataset_ids_excluded": matched,
              "eligible_tasks": len(eligible), "groups": groups, "script_sha256": sha(Path(__file__)),
              "selection": "Hash order over stable task IDs after exact stripped-question hash exclusion, independent of answer or outcome. First8pilot,next40evaluation; no replacements.",
              "status": "Inputs prepared; model grid and inferential protocol not yet registered or executed.",
              "limits": "Public development data, not guaranteed unseen in pretraining. Distractor-context snapshot differs from live full-Wikipedia retrieval. Selection is not a completed experiment."}
    (ROOT / "research/evidence/hotpot_snapshot_selection_v1.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"pilot": 8, "evaluation": 40, "archive_questions_excluded": len(matched), "eligible": len(eligible)}))


if __name__ == "__main__":
    main()
