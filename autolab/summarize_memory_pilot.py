"""Validate completeness and summarize an exploratory memory pilot without pooling versions."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def summarize(root):
    conditions = ("none", "raw", "reflection", "scoped")
    expected = {(case, c) for case in range(12) for c in conditions}
    trials = {}
    hashes = {}
    for path in sorted(root.glob("case-*-target-*.json")):
        data = path.read_bytes()
        d = json.loads(data)
        key = (d["metadata"]["case"], d["metadata"]["condition"])
        if key in trials or key not in expected:
            raise ValueError(f"Duplicate or unexpected trial: {key}")
        trials[key] = d
        hashes[path.name] = hashlib.sha256(data).hexdigest()
    rows = []
    for c in conditions:
        ds = [d for (case, condition), d in trials.items() if condition == c]
        rows.append({"condition": c, "n": len(ds),
                     "successes": sum(d["evaluation"]["success"] is True for d in ds),
                     "unknown_evaluations": sum(d["evaluation"]["success"] is None for d in ds),
                     "protocol_errors": sum("protocol_error" in t for d in ds for t in d["trace"]),
                     "terminations": dict(Counter(d["termination"] for d in ds)),
                     "input_tokens": sum(d["usage"]["input_tokens"] for d in ds),
                     "output_tokens": sum(d["usage"]["output_tokens"] for d in ds)})
    missing = sorted(expected - trials.keys())
    pairs = []
    for case in range(12):
        if all((case, c) in trials for c in conditions):
            ds = [trials[case, c] for c in conditions]
            if len({d["task_sha256"] for d in ds}) != 1 or len({d["prompt_sha256"] for d in ds}) != 1:
                raise ValueError("Paired task or protocol mismatch")
            pairs.append({"case": case, **{c: trials[case, c]["evaluation"]["success"] for c in conditions}})
    source_counts = Counter()
    for p in sorted(root.glob("case-*-source.json")):
        d = json.loads(p.read_text())
        source_counts[str(d["evaluation"]["success"])] += 1
    return {"purpose": "development_only_not_paper_evidence", "root": str(root),
            "complete": not missing, "missing": missing, "conditions": rows,
            "source_success_counts": dict(source_counts), "pairs": pairs,
            "target_file_sha256": hashes,
            "cost_scope": "target costs only here; source and curation costs remain in their raw artifacts"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    print(json.dumps(summarize(args.root), indent=2))
