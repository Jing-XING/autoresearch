"""Build a complete fixed NK-schema bank without quality-based source selection."""
import argparse
import hashlib
import json
from pathlib import Path

from .experience_memory_bank import FixedMemoryBank
from .local_smoke import sha256_file as sha
from .nk_prefix_comparator import CONDITIONS, LIMIT, validate_reply
from .nk_prefix_curation import load_prepared


SOURCE_BANK_SHA = "52928f597ba4f0baa9d8794130f674ba47038e43eca4fca6654abda4c8b04875"


def validate_outcome(value, packet):
    for field in ("record_id", "condition", "input", "input_sha256"):
        if value.get(field) != packet[field]:
            raise ValueError("Curation input identity changed")
    status = value.get("status")
    if status == "generation_error":
        if "reply" in value or not isinstance(value.get("error_type"), str):
            raise ValueError("Inconsistent generation error")
        return "", status
    if status not in ("valid_memory", "invalid_memory"):
        raise ValueError("Unknown curation status")
    reply = value["reply"]
    parsed, errors = validate_reply(reply["text"], packet["record_id"], reply["output_tokens"])
    expected = "invalid_memory" if errors else "valid_memory"
    if status != expected or value.get("parsed") != parsed or value.get("validation_errors") != errors:
        raise ValueError("Stored validation disagrees with raw reply")
    return (reply["text"] if status == "valid_memory" else ""), status


def build_bank(prepared, curation, source_bank, registration):
    preparation, packets = load_prepared(prepared)
    registered = json.loads(registration.read_bytes())
    if registered["batch"] != "nk-prefix-curation-v1" or registered["preparation_manifest_sha256"] != sha(prepared / "manifest.json"):
        raise ValueError("Curation registration mismatch")
    if sha(source_bank) != SOURCE_BANK_SHA:
        raise ValueError("Original source bank changed")
    original = json.loads(source_bank.read_bytes())
    source_by_id = {r["record_id"]: r for r in original["records"]}
    selected = preparation["selected_record_ids"]
    if not set(selected) <= set(source_by_id):
        raise ValueError("Eligible sources missing from original bank")
    expected_models = original["curation_manifests"][0]["configuration"]["model_files_sha256"]
    outcomes, manifests, shared = {}, {}, None
    files = sorted(curation.glob("shard-*/manifest.json"))
    if len(files) != 4:
        raise ValueError("Require all four curation shards")
    for path in files:
        manifest = json.loads(path.read_bytes())
        shard = manifest["shard"]
        if type(shard) is not int or shard not in range(4) or shard in manifests or manifest["shards"] != 4:
            raise ValueError("Invalid shard identity")
        if manifest["schema"] != "autolab.nk_prefix_curation.v1" or manifest["preparation"] != preparation:
            raise ValueError("Preparation content changed")
        if manifest["preparation_manifest_sha256"] != sha(prepared / "manifest.json"):
            raise ValueError("Preparation bytes changed")
        if manifest["model_files_sha256"] != expected_models:
            raise ValueError("Curator checkpoint changed")
        config = {k: manifest[k] for k in ("source_sha256", "model_files_sha256", "packages", "decoding", "seed", "max_new_tokens")}
        expected_source = {k: registered["source_files_sha256"]["autolab/" + k]
                           for k in ("nk_prefix_curation.py", "nk_prefix_comparator.py", "local_smoke.py", "tool_agent.py")}
        if config["source_sha256"] != expected_source or config["model_files_sha256"] != registered["model_files_sha256"]:
            raise ValueError("Curation code or checkpoint differs from registration")
        if config["max_new_tokens"] != LIMIT or config["decoding"] != "greedy" or config["seed"] != 20260919:
            raise ValueError("Generation configuration changed")
        if shared is not None and config != shared:
            raise ValueError("Curation configuration changed across shards")
        shared = config
        ids = selected[shard::4]
        if manifest["selected_record_ids"] != ids:
            raise ValueError("Selected shard records changed")
        manifests[shard] = {"manifest_sha256": sha(path)}
        summary = json.loads((path.parent / "summary.json").read_bytes())
        rows = []
        for uid in ids:
            for condition in CONDITIONS:
                key = uid, condition
                output = path.parent / f"{uid}-{condition}.json"
                value = json.loads(output.read_bytes())
                memory, status = validate_outcome(value, packets[key])
                outcomes[key] = {"memory": memory, "status": status, "file_sha256": sha(output),
                                 "usage": {k: value.get("reply", {}).get(k) for k in
                                           ("input_tokens", "output_tokens", "elapsed_seconds")}}
                rows.append({"record_id": uid, "condition": condition, "status": status})
        if summary["rows"] != rows or summary["expected_records"] != len(rows):
            raise ValueError("Curation summary coverage changed")
    if set(outcomes) != set(packets):
        raise ValueError("Incomplete curation coverage")
    records = []
    for uid in selected:
        source = source_by_id[uid]
        records.append({"record_id": uid, "ticket": source["ticket"], "source_model": source["source_model"],
                        "memories": {"raw": source["memories"]["raw"],
                                     **{c: outcomes[(uid, c)]["memory"] for c in CONDITIONS}},
                        "curation": {c: {k: v for k, v in outcomes[(uid, c)].items() if k != "memory"}
                                     for c in CONDITIONS}})
    return {"schema": "autolab.fixed_experience_bank.v1", "adaptation": "autolab.nk_prefix_bank.v1",
            "source_task_ids": original["source_task_ids"], "source_cutoff": 8,
            "source_bank_sha256": SOURCE_BANK_SHA, "preparation_manifest_sha256": sha(prepared / "manifest.json"),
            "curation_registration_sha256": sha(registration),
            "curation_configuration": shared, "curation_manifests": manifests, "records": records,
            "invalid_policy": "retain source selection; empty experience with unchanged common wrapper"}


class NKMemoryBank(FixedMemoryBank):
    def __init__(self, value):
        if value.get("adaptation") != "autolab.nk_prefix_bank.v1":
            raise ValueError("Not a validated NK-schema bank")
        super().__init__(value)
        self.by_id = {r["record_id"]: r for r in self.records}
        for record in self.records:
            for condition in CONDITIONS:
                if not isinstance(record["memories"].get(condition), str):
                    raise ValueError("Missing condition memory")
                status = record["curation"][condition]["status"]
                if status not in ("valid_memory", "invalid_memory", "generation_error"):
                    raise ValueError("Invalid recorded curation status")
                if status != "valid_memory" and record["memories"][condition]:
                    raise ValueError("Invalid curation must not be injected")

    def retrieve(self, ticket, condition):
        if condition not in CONDITIONS:
            raise ValueError("Invalid NK-schema condition")
        # Select on the complete eligible pool before reading curation quality.
        selected = super().retrieve(ticket, "raw")
        record = self.by_id[selected["record_id"]]
        memory = record["memories"][condition]
        return {**selected, "condition": condition, "memory": memory,
                "curation_status": record["curation"][condition]["status"],
                "memory_sha256": hashlib.sha256(memory.encode()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("prepared", "curation", "source-bank", "registration", "output"):
        parser.add_argument("--" + arg, type=Path, required=True)
    args = parser.parse_args()
    bank = build_bank(args.prepared, args.curation, args.source_bank, args.registration)
    NKMemoryBank(bank)
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(bank, f, ensure_ascii=False, indent=2)
    print(json.dumps({"sources": len(bank["records"]), "sha256": sha(args.output)}))


if __name__ == "__main__":
    main()
