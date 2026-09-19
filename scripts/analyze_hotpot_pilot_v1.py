"""Validate a closed frozen 48-episode grid before opening pilot-only gold."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from autolab.hotpot_analysis import require, summarize, validate_episode
from autolab.hotpot_pilot import CONDITIONS, SETTINGS
from autolab.hotpot_snapshot import ROOT, load_answer_scorer


def sha(data):
    return hashlib.sha256(data).hexdigest()


def validate_grid(root, archive, receipt_path):
    receipt = json.loads(receipt_path.read_bytes())
    require(sha(archive.read_bytes()) == receipt["archive_sha256"], "Deployment archive hash mismatch")
    with zipfile.ZipFile(archive) as z:
        require(len(z.namelist()) == len(set(z.namelist())) == receipt["archive_entries"], "Archive member mismatch")
        payload = {name: z.read(name) for name in receipt["files_sha256"]}
    require({n: sha(b) for n, b in payload.items()} == receipt["files_sha256"], "Deployment payload mismatch")
    for name, data in payload.items():
        if name.startswith("autolab/") or name.startswith("results/third_party/") or name.endswith("speculative_action_source_manifest_v1.json"):
            require((ROOT / name).read_bytes() == data, "Local replay code/source differs: " + name)
    registered = json.loads(payload["protocol/registration.json"])
    selection_bytes = payload["research/evidence/hotpot_snapshot_selection_v1.json"]
    selection = json.loads(selection_bytes)
    inputs_bytes = payload["inputs/pilot.json"]
    items = json.loads(inputs_bytes)
    require(sha(selection_bytes) == registered["selection_sha256"], "Selection hash mismatch")
    require(sha(inputs_bytes) == registered["pilot_inputs_sha256"] == selection["groups"]["pilot"]["inputs_sha256"], "Inputs hash mismatch")
    require(len(items) == 8 and [i["id"] for i in items] == selection["groups"]["pilot"]["ids"], "Pilot identity mismatch")
    grid_path = root / "grid_manifest.json"
    grid = json.loads(grid_path.read_bytes())
    require(grid["batch"] == "hotpot-pilot-v1" and grid["status"] == "complete"
            and grid["registered_episodes"] == 48 and grid["registration"] == registered, "Grid not closed or registration differs")
    expected_workers = {(model, shard) for model in ("qwen3", "qwen25") for shard in (0, 1)}
    require(len(grid["workers"]) == 4 and {(w["model"], w["shard"]) for w in grid["workers"]} == expected_workers, "Worker identity mismatch")
    require(all(w.get("exit_code") == 0 and w["episodes"] == 12 for w in grid["workers"]), "Unsuccessful worker")
    expected_cases = {f"{m}/shard-{i % 2}/case-{i:03d}-{c}.json" for m in ("qwen3", "qwen25") for i in range(8) for c in CONDITIONS}
    require({p.relative_to(root).as_posix() for p in root.rglob("case-*.json")} == expected_cases, "Missing or extra cases")
    expected_manifests = {f"{m}/shard-{s}/manifest.json" for m, s in expected_workers}
    require({p.relative_to(root).as_posix() for p in root.rglob("manifest.json")} == expected_manifests, "Missing or extra manifests")
    hashes = {"grid_manifest.json": sha(grid_path.read_bytes())}
    rows = []
    for model, shard in sorted(expected_workers):
        folder = root / model / f"shard-{shard}"
        manifest = json.loads((folder / "manifest.json").read_bytes())
        reference = json.loads(payload[f"protocol/{model}.json"])
        expected = {"settings": SETTINGS, "conditions": list(CONDITIONS),
            "selected_ids": [i["id"] for i in items[shard::2]], "selection_sha256": sha(selection_bytes),
            "inputs_sha256": sha(inputs_bytes), "model_files_sha256": reference["model_files_sha256"],
            "model_reference_sha256": sha(payload[f"protocol/{model}.json"]), "shard": shard, "shards": 2,
            "decoder": "greedy_native_chat_template_empty_tool_list", "seed": 20260919,
            "condition_order": "Rotate baseline/shared/isolated by original pilot index modulo three",
            "source_sha256": {n: sha(payload["autolab/" + n]) for n in
                ("hotpot_pilot.py", "hotpot_snapshot.py", "native_tool_agent.py", "local_smoke.py", "tool_agent.py")}}
        require(all(manifest.get(k) == v for k, v in expected.items()), "Worker manifest differs: " + str(folder))
        # Preserve placement/package metadata without inventing a runtime match.
        for path in (folder / "manifest.json", folder / "model_placement.json"):
            json.loads(path.read_bytes())
            hashes[path.relative_to(root).as_posix()] = sha(path.read_bytes())
        for index in range(shard, 8, 2):
            for condition in CONDITIONS:
                path = folder / f"case-{index:03d}-{condition}.json"
                data = path.read_bytes()
                row = json.loads(data)
                audit = validate_episode(row, items[index], condition)
                hashes[path.relative_to(root).as_posix()] = sha(data)
                rows.append(dict(row, model=model, replay_audit=audit))
    return rows, selection, hashes


def analyze(root, archive, receipt, gold_path):
    rows, selection, hashes = validate_grid(root, archive, receipt)
    data_manifest = ROOT / "research/evidence/hotpot_control_data_manifest_v1.json"
    require(sha(data_manifest.read_bytes()) == selection["source_manifest_sha256"], "Scorer/data manifest differs from selection")
    # Intentionally after every artifact and all 48 replays passed.
    gold_bytes = gold_path.read_bytes()
    require(sha(gold_bytes) == selection["groups"]["pilot"]["gold_sha256"], "Pilot gold hash mismatch")
    report = summarize(rows, json.loads(gold_bytes), load_answer_scorer())
    report["provenance"] = {"archive_sha256": sha(archive.read_bytes()), "receipt_sha256": sha(receipt.read_bytes()),
        "pilot_gold_sha256": sha(gold_bytes), "raw_files_sha256": hashes,
        "data_manifest_sha256": sha(data_manifest.read_bytes()),
        "answer_scorer_sha256": sha((ROOT / "results/third_party/hotpotqa-control/hotpot_evaluate_v1.py").read_bytes()),
        "workers": [{"model": m, "shard": s,
            "manifest": json.loads((root / m / f"shard-{s}/manifest.json").read_bytes()),
            "placement": json.loads((root / m / f"shard-{s}/model_placement.json").read_bytes())}
            for m in ("qwen3", "qwen25") for s in (0, 1)],
        "analysis_files_sha256": {p: sha((ROOT / p).read_bytes()) for p in
            ("autolab/hotpot_analysis.py", "scripts/analyze_hotpot_pilot_v1.py")}}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("root", "archive", "receipt", "gold", "output"):
        parser.add_argument("--" + arg, type=Path, required=True)
    args = parser.parse_args()
    report = analyze(args.root, args.archive, args.receipt, args.gold)
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, allow_nan=False)


if __name__ == "__main__":
    main()
