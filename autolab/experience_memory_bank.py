"""Build and retrieve a fixed, paired experience bank without outcome selection.

Retrieval uses source and target ticket words, never the hidden task name,
reward, future continuation, or generated lesson. This intentionally simple
retriever is a controlled baseline; its quality is not assumed optimal.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re

from autolab.experience_curator import CONDITIONS, curator_messages
from autolab.local_smoke import sha256_file
from autolab.trajectory_cutoffs import digest


def ticket_from_payload(payload):
    text = "\n".join(m["content"] for m in payload["system_messages"])
    matches = re.findall(r"<ticket>\s*(.*?)\s*</ticket>", text, re.S)
    if len(matches) != 1:
        raise ValueError("Expected exactly one visible source ticket")
    return matches[0]


def build_bank(cutoff_root, curation_root, cutoff=8):
    source_manifest = json.loads((cutoff_root / "manifest.json").read_bytes())
    sources = [r for r in source_manifest["records"] if r["cutoff"] == cutoff]
    if not sources or len({r["record_id"] for r in sources}) != len(sources):
        raise ValueError("No source records or duplicate source identities")
    outputs, manifests = {}, []
    for manifest_file in sorted(curation_root.rglob("manifest.json")):
        manifest = json.loads(manifest_file.read_bytes())
        if manifest["generation_cutoff"] != cutoff or set(manifest["conditions"]) != set(CONDITIONS):
            raise ValueError("Incompatible curation conditions or cutoff")
        comparable = {k: manifest[k] for k in ("seed", "decoding", "max_new_tokens", "source_sha256", "model_files_sha256")}
        if "prompt_contract" in manifest:
            comparable["prompt_contract"] = manifest["prompt_contract"]
        if manifests and comparable != manifests[0]["configuration"]:
            raise ValueError("Curator configuration changed across shards")
        manifests.append({"file": manifest_file.relative_to(curation_root).as_posix(),
                          "sha256": sha256_file(manifest_file), "configuration": comparable})
        for record_id in manifest["selected_record_ids"]:
            for condition in CONDITIONS:
                file = manifest_file.parent / f"{record_id}-{condition}.json"
                output = json.loads(file.read_bytes())
                key = (record_id, condition)
                if key in outputs or output.get("status") != "generated":
                    raise ValueError("Duplicate or failed curation; do not silently select successful records")
                if output["record_id"] != record_id or output["condition"] != condition:
                    raise ValueError("Curation identity mismatch")
                outputs[key] = (output, sha256_file(file))
    expected = {(r["record_id"], c) for r in sources for c in CONDITIONS}
    if set(outputs) != expected:
        raise ValueError("Curation coverage does not match the complete source pool")
    records, hashes = [], {}
    for source in sources:
        record_id = source["record_id"]
        payload = json.loads((cutoff_root / "inputs" / f"{record_id}.json").read_bytes())
        if digest(payload) != source["payload_sha256"]:
            raise ValueError("Visible source input hash mismatch")
        # Do not open labels/. Only the manifest task identity is retained for
        # overlap guards; it is never a retrieval feature or agent input.
        ticket = ticket_from_payload(payload)
        memories = {"raw": json.dumps({"source_ticket": ticket,
                    "observed_history": payload["observed_messages"],
                    "stop_reason": payload["stop_reason"],
                    "observed_benchmark_reward": payload["observed_benchmark_reward"],
                    "generation_budget": payload["generation_budget"]}, sort_keys=True)}
        usage = {}
        for condition in CONDITIONS:
            output, file_hash = outputs[(record_id, condition)]
            messages = curator_messages(payload, condition, manifests[0]["configuration"].get("prompt_contract", "legacy"))
            prompt_hash = hashlib.sha256(json.dumps(messages, sort_keys=True).encode()).hexdigest()
            if output["input"] != messages or output["input_sha256"] != prompt_hash:
                raise ValueError("Curator used different evidence or instruction")
            memories[condition] = output["reply"]["text"]
            usage[condition] = {k: output["reply"][k] for k in ("input_tokens", "output_tokens", "elapsed_seconds")}
            hashes[f"{record_id}-{condition}"] = file_hash
        records.append({"record_id": record_id, "source_model": source["model"],
                        "ticket": ticket, "memories": memories, "curation_usage": usage})
    return {"schema": "autolab.fixed_experience_bank.v1", "purpose": "development transfer experiment",
            "source_task_ids": sorted({r["cluster_id"] for r in sources}),
            "source_exclusions": source_manifest.get("excluded", []),
            "source_cutoff": cutoff, "retrieval": "ticket TF-IDF cosine; top-1; record-id tie break",
            "source_manifest_sha256": sha256_file(cutoff_root / "manifest.json"),
            "curation_manifests": manifests, "curation_artifact_sha256": hashes, "records": records}


def words(text):
    # Do not match literal customer IDs/phone numbers from a source episode.
    return re.findall(r"\b[a-z]{2,}\b", text.casefold())


class FixedMemoryBank:
    def __init__(self, value):
        if value["schema"] != "autolab.fixed_experience_bank.v1" or not value["records"]:
            raise ValueError("Invalid or empty memory bank")
        self.value = value
        self.records = sorted(value["records"], key=lambda r: r["record_id"])
        if len({r["record_id"] for r in self.records}) != len(self.records):
            raise ValueError("Duplicate bank record identity")
        df = Counter(token for record in self.records for token in set(words(record["ticket"])))
        self.idf = {token: math.log((1 + len(self.records)) / (1 + count)) + 1 for token, count in df.items()}
        self.vectors = [self.vector(r["ticket"]) for r in self.records]

    def vector(self, text):
        tf = Counter(words(text))
        weights = {t: (1 + math.log(n)) * self.idf[t] for t, n in tf.items() if t in self.idf}
        norm = math.sqrt(sum(w * w for w in weights.values()))
        return {t: w / norm for t, w in weights.items()} if norm else {}

    def assert_disjoint(self, target_ids):
        if set(target_ids) & set(self.value["source_task_ids"]):
            raise ValueError("Source/target task overlap; transfer evaluation rejected")

    def retrieve(self, ticket, condition):
        if condition not in ("raw", *CONDITIONS):
            raise ValueError("Invalid memory condition")
        query = self.vector(ticket)
        scores = [sum(query.get(t, 0) * w for t, w in vector.items()) for vector in self.vectors]
        best = max(scores)
        tied = [i for i, score in enumerate(scores) if abs(score - best) <= 1e-12]
        index = tied[0]
        record = self.records[index]
        return {"record_id": record["record_id"], "similarity": scores[index],
                "tied_candidates": len(tied), "pool_size": len(self.records),
                "condition": condition, "memory": record["memories"][condition]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cutoff-root", type=Path, required=True)
    parser.add_argument("--curation-root", type=Path, required=True)
    parser.add_argument("--cutoff", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    bank = build_bank(args.cutoff_root, args.curation_root, args.cutoff)
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(bank, f, indent=2)
    print(json.dumps({"records": len(bank["records"]), "source_tasks": len(bank["source_task_ids"])}))


if __name__ == "__main__":
    main()
