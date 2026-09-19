"""Execute frozen NK-schema prompts once and retain every curation outcome."""
import argparse
from dataclasses import asdict
import importlib.metadata
import json
from pathlib import Path

from .local_smoke import LocalTransformersModel, sha256_file
from .nk_prefix_comparator import CONDITIONS, LIMIT, digest, validate_reply
from .tool_agent import write_episode


def load_prepared(root):
    manifest = json.loads((root / "manifest.json").read_bytes())
    if manifest.get("schema") != "autolab.nk_prefix_inputs.v1":
        raise ValueError("Unknown preparation schema")
    if manifest["max_new_tokens"] != LIMIT or manifest["decoding"] != "greedy":
        raise ValueError("Preparation generation settings changed")
    if manifest["source_sha256"] != sha256_file(Path(__file__).with_name("nk_prefix_comparator.py")):
        raise ValueError("Prepared comparator source changed")
    ids = manifest["selected_record_ids"]
    if not ids or ids != sorted(set(ids)):
        raise ValueError("Invalid ordered source pool")
    expected = {(uid, condition) for uid in ids for condition in CONDITIONS}
    packets = {}
    for row in manifest["rows"]:
        key = (row["record_id"], row["condition"])
        filename = f"{key[0]}-{key[1]}.json"
        if row["file"] != filename or Path(filename).name != filename:
            raise ValueError("Invalid packet path")
        path = root / filename
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("Packet outside preparation directory")
        value = json.loads(path.read_bytes())
        if key in packets or key not in expected:
            raise ValueError("Unexpected or duplicate packet identity")
        if (value.get("record_id"), value.get("condition")) != key:
            raise ValueError("Packet identity does not match manifest")
        actual = digest(value["input"])
        if actual != row["input_sha256"] or actual != value["input_sha256"]:
            raise ValueError("Prepared prompt changed")
        if len(value["input"]) != 2 or [r["role"] for r in value["input"]] != ["system", "user"]:
            raise ValueError("Invalid message format")
        packets[key] = value
    if set(packets) != expected:
        raise ValueError("Incomplete prepared condition grid")
    for uid in ids:
        a, b = (packets[(uid, condition)]["input"] for condition in CONDITIONS)
        if a[1] != b[1] or a[0] == b[0]:
            raise ValueError("Paired evidence or intervention changed")
    return manifest, packets


def generate_packet(model, packet):
    # Copy metadata only; the model receives precisely the frozen messages.
    result = {"record_id": packet["record_id"], "condition": packet["condition"],
              "input": packet["input"], "input_sha256": packet["input_sha256"]}
    try:
        reply = model.generate(packet["input"], LIMIT)
        value, errors = validate_reply(reply.text, packet["record_id"], reply.output_tokens)
        result.update(reply=asdict(reply), parsed=value, validation_errors=errors,
                      status="invalid_memory" if errors else "valid_memory")
    except Exception as exc:
        result.update(status="generation_error", error_type=type(exc).__name__, error=str(exc))
    return result


def run_packets(model, packets, selected_ids, output):
    """No retry, schema repair, or filtering after observing generation quality."""
    rows = []
    for uid in selected_ids:
        for condition in CONDITIONS:
            result = generate_packet(model, packets[(uid, condition)])
            write_episode(result, output, f"{uid}-{condition}")
            row = {"record_id": uid, "condition": condition, "status": result["status"]}
            rows.append(row)
            print(json.dumps(row), flush=True)
    summary = {"rows": rows, "expected_records": len(selected_ids) * len(CONDITIONS),
               "valid": sum(r["status"] == "valid_memory" for r in rows),
               "invalid": sum(r["status"] == "invalid_memory" for r in rows),
               "generation_errors": sum(r["status"] == "generation_error" for r in rows)}
    write_episode(summary, output, "summary")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--shard", type=int, default=0)
    parser.add_argument("--shards", type=int, default=4)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--expected-model-hashes", type=Path)
    args = parser.parse_args()
    if args.shards < 1 or not 0 <= args.shard < args.shards:
        parser.error("Invalid shard")
    preparation, packets = load_prepared(args.prepared)
    selected = preparation["selected_record_ids"][args.shard::args.shards]
    if not selected:
        parser.error("Empty source shard")
    if args.preflight_only:
        print(json.dumps({"preflight": "passed", "total_sources": len(preparation["selected_record_ids"]),
                          "shard_sources": len(selected), "model_loaded": False}))
        return
    if args.output.exists():
        raise FileExistsError(args.output)
    if args.expected_model_hashes is None:
        parser.error("Execution requires frozen model file hashes")
    manifest = {"schema": "autolab.nk_prefix_curation.v1", "preparation": preparation,
                "preparation_manifest_sha256": sha256_file(args.prepared / "manifest.json"),
                "max_new_tokens": LIMIT, "decoding": "greedy", "seed": 20260919,
                "selected_record_ids": selected, "shard": args.shard, "shards": args.shards,
                "source_sha256": {name: sha256_file(Path(__file__).with_name(name)) for name in
                    ("nk_prefix_curation.py", "nk_prefix_comparator.py", "local_smoke.py", "tool_agent.py")},
                "packages": {name: importlib.metadata.version(name) for name in ("torch", "transformers", "accelerate")},
                "model_files_sha256": {p.name: sha256_file(p) for p in sorted(args.model_path.iterdir())
                    if p.is_file() and (p.suffix in (".json", ".safetensors") or p.name == "merges.txt")}}
    if manifest["model_files_sha256"] != json.loads(args.expected_model_hashes.read_bytes()):
        raise ValueError("Curator model files differ from the registered checkpoint")
    args.output.mkdir(parents=True, exist_ok=False)
    write_episode(manifest, args.output, "manifest")
    model = LocalTransformersModel(args.model_path)
    run_packets(model, packets, selected, args.output)


if __name__ == "__main__":
    main()
