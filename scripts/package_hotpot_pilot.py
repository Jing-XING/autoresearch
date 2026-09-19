"""Package pilot inputs and fixed code only; no gold or evaluation task passages."""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    paths = ["autolab/" + name + ".py" for name in
             ["__init__", "runner", "tool_agent", "local_smoke", "native_tool_agent", "hotpot_snapshot", "hotpot_pilot"]]
    paths += ["tests/test_hotpot_pilot.py", "scripts/run_hotpot_pilot_v1.py",
              "research/hotpot_pilot_protocol_v1.md", "research/evidence/hotpot_snapshot_selection_v1.json",
              "research/evidence/speculative_action_source_manifest_v1.json"]
    paths += ["results/third_party/speculative-action/source/hotpotqa/src/" + x + ".py" for x in ["environment", "prompts"]]
    contents = {p: (ROOT / p).read_bytes() for p in paths}
    public_path = ROOT / "results/preparations/hotpot-snapshot-control-v1/pilot.inputs.json"
    contents["inputs/pilot.json"] = public_path.read_bytes()
    assert all(set(r) == {"id", "question", "context"} for r in json.loads(contents["inputs/pilot.json"]))
    references = {}
    for model in ["qwen3", "qwen25"]:
        path = ROOT / f"results/remote/vakra-permissive-v1/runs/vakra-permissive-v1/cars/original/{model}/shard-0/manifest.json"
        prior = json.loads(path.read_bytes())
        ref = {"model": model, "prior_manifest_sha256": sha(path), "model_files_sha256": prior["model_files_sha256"]}
        contents[f"protocol/{model}.json"] = json.dumps(ref, indent=2).encode()
        references[model] = ref
    registration = {"batch": "hotpot-pilot-v1", "registered_episodes": 48, "pilot_tasks": 8,
        "models": list(references), "conditions": ["baseline", "shared", "isolated"],
        "selection_sha256": sha(ROOT / "research/evidence/hotpot_snapshot_selection_v1.json"),
        "pilot_inputs_sha256": sha(public_path), "protocol_sha256": sha(ROOT / "research/hotpot_pilot_protocol_v1.md"),
        "model_references": references, "evaluation_tasks_deployed": 0, "gold_labels_deployed": False,
        "predecessor": "tau-nk-test40-v2", "purpose": "Development pilot of measurement-state isolation, not a novel scheduler or completed paper"}
    contents["protocol/registration.json"] = json.dumps(registration, indent=2).encode()
    hashes = {n: hashlib.sha256(data).hexdigest() for n, data in sorted(contents.items())}
    contents["package_files.json"] = json.dumps(hashes, indent=2).encode()
    archive = ROOT / "results/deploy/hotpot-pilot-v1.zip"
    with ZipFile(archive, "x", ZIP_DEFLATED) as z:
        for name, data in sorted(contents.items()):
            assert not any(s in name for s in [".env", ".gold.", "evaluation.inputs", "hotpot_dev_distractor"])
            z.writestr(name, data)
    record = dict(registration, archive_sha256=sha(archive), archive_bytes=archive.stat().st_size,
                  archive_entries=len(contents), files_sha256=hashes)
    evidence = ROOT / "research/evidence/hotpot_pilot_registration_v1.json"
    with evidence.open("x", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
    receipt = json.dumps({"archive_sha256": sha(archive), "files_verified": len(hashes)}, sort_keys=True).encode()
    (ROOT / "results/deploy/hotpot-pilot-v1-receipt-expected.json").write_bytes(receipt)
    print(json.dumps({"bytes": archive.stat().st_size, "entries": len(contents), "sha256": sha(archive),
                      "receipt_sha256": hashlib.sha256(receipt).hexdigest()}))


if __name__ == "__main__":
    main()
