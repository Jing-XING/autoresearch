"""Acquire official HotpotQA distractor development data and pin its scorer.

No benchmark or model execution. Download URLs are linked by hotpotqa.github.io.
"""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DATA_URL = "https://curtis.ml.cmu.edu/datasets/hotpot/hotpot_dev_distractor_v1.json"
HF_COMMIT = "1908d6afbbead072334abe2965f91bd2709910ab"
HF_FILE = "distractor/validation-00000-of-00001.parquet"
HF_SHA256 = "c20b638ca82b21d04fe12e14ff417ad05153d4d215a65de54497fca4e972f7c6"


def get(url, limit):
    request = urllib.request.Request(url, headers={"User-Agent": "reproducible-agent-research"})
    with urllib.request.urlopen(request, timeout=45) as response:
        data = response.read(limit + 1)
        assert len(data) <= limit
        return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hf-mirror", action="store_true", help="Use the explicitly pinned Hugging Face representation after original-host timeout")
    args = parser.parse_args()
    target = ROOT / "results/third_party/hotpotqa-control"
    target.mkdir(parents=True, exist_ok=True)
    data_path = target / "hotpot_dev_distractor_v1.json"
    mirror = None
    if args.hf_mirror:
        import pyarrow.parquet as pq
        parquet_path = target / "hotpot_dev_distractor.parquet"
        url = f"https://huggingface.co/datasets/hotpotqa/hotpot_qa/resolve/{HF_COMMIT}/{HF_FILE}"
        if not parquet_path.exists():
            blob = get(url, 40_000_000)
            assert hashlib.sha256(blob).hexdigest() == HF_SHA256
            parquet_path.write_bytes(blob)
        assert hashlib.sha256(parquet_path.read_bytes()).hexdigest() == HF_SHA256
        records = []
        for row in pq.read_table(parquet_path).to_pylist():
            context, facts = row.pop("context"), row.pop("supporting_facts")
            row["_id"] = row.pop("id")
            row["context"] = list(map(list, zip(context["title"], context["sentences"], strict=True)))
            row["supporting_facts"] = list(map(list, zip(facts["title"], facts["sent_id"], strict=True)))
            records.append(row)
        data = json.dumps(records, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if data_path.exists():
            assert data_path.read_bytes() == data
        else:
            data_path.write_bytes(data)
        mirror = {"repository": "hotpotqa/hotpot_qa", "commit": HF_COMMIT, "url": url,
                  "parquet_sha256": HF_SHA256, "parquet_bytes": parquet_path.stat().st_size,
                  "conversion": "id to _id; context and supporting-facts structs to row-pair lists, with no semantic filtering or order changes.",
                  "original_host_failure": "HTTPS TLS handshake timeout after sandbox network retry; no certificate verification disabled."}
    elif not data_path.exists():
        data = get(DATA_URL, 60_000_000)
        records = json.loads(data)
        assert isinstance(records, list) and len(records) == 7405
        with data_path.open("xb") as f:
            f.write(data)
    else:
        data = data_path.read_bytes()
        records = json.loads(data)
    assert len(records) == len({r["_id"] for r in records}) == 7405
    assert all(set(["_id", "question", "answer", "context", "supporting_facts"]) <= r.keys() for r in records)
    pin_path = target / "scorer_commit.json"
    if not pin_path.exists():
        commit_data = get("https://api.github.com/repos/hotpotqa/hotpot/commits/master", 1_000_000)
        pin_path.write_bytes(commit_data)
    revision = json.loads(pin_path.read_bytes())["sha"]
    assert len(revision) == 40 and all(c in "0123456789abcdef" for c in revision)
    scorer_path = target / "hotpot_evaluate_v1.py"
    url = f"https://raw.githubusercontent.com/hotpotqa/hotpot/{revision}/hotpot_evaluate_v1.py"
    if not scorer_path.exists():
        scorer_path.write_bytes(get(url, 100_000))
    manifest = {
        "purpose": __doc__, "dataset_source": mirror["url"] if mirror else DATA_URL,
        "original_dataset_url": DATA_URL, "mirror": mirror,
        "dataset_bytes": len(data), "dataset_sha256": hashlib.sha256(data).hexdigest(),
        "records": len(records), "license_page": "https://hotpotqa.github.io/",
        "license": "CC BY-SA 4.0, attribution and source links retained; see dataset homepage",
        "scorer_repository": "hotpotqa/hotpot", "scorer_commit": revision,
        "scorer_url": url, "scorer_sha256": hashlib.sha256(scorer_path.read_bytes()).hexdigest(),
        "dataset_pin_note": "Receipt pins source bytes and any declared conversion. Converted JSON is not claimed byte-identical to the unavailable original-host JSON.",
        "model_experiments": 0,
    }
    dest = ROOT / "research/evidence/hotpot_control_data_manifest_v1.json"
    with dest.open("x", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(json.dumps({k: manifest[k] for k in ["records", "dataset_bytes", "dataset_sha256", "scorer_commit"]}))


if __name__ == "__main__":
    main()
