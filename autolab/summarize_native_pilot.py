"""Audit a paired native-tool development pilot; report descriptive, paired outcomes."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def summarize(root):
    conditions = ("none", "raw", "reflection", "scoped")
    expected = {(case, limit, c) for case in range(12) for limit in (2, 4) for c in conditions}
    trials, hashes = {}, {}
    for path in sorted(root.glob("shard-*/case-*-target-*.json")):
        raw = path.read_bytes()
        data = json.loads(raw)
        m = data["metadata"]
        key = (m["case"], m["source_tool_budget"], m["condition"])
        if key not in expected or key in trials:
            raise ValueError(f"Unexpected or duplicate target {key}")
        if type(data["evaluation"]["success"]) is not bool:
            raise ValueError(f"Non-boolean evaluation {key}")
        trials[key] = data
        hashes[str(path.relative_to(root))] = hashlib.sha256(raw).hexdigest()
    for case in range(12):
        group = [d for (i, _, _), d in trials.items() if i == case]
        for field in ("task_sha256", "prompt_sha256"):
            if len({d[field] for d in group}) > 1:
                raise ValueError(f"Mismatched paired {field}: {case}")
        if len({json.dumps(d['budget'], sort_keys=True) for d in group}) > 1:
            raise ValueError(f"Mismatched target budget: {case}")
    groups = []
    for limit in (2, 4):
        for condition in conditions:
            ds = [d for (_, b, c), d in trials.items() if b == limit and c == condition]
            groups.append({"source_tool_budget": limit, "condition": condition, "n": len(ds),
                           "successes": sum(d["evaluation"]["success"] for d in ds),
                           "protocol_errors": sum("protocol_error" in t for d in ds for t in d["trace"]),
                           "terminations": dict(Counter(d["termination"] for d in ds)),
                           "usage": {k: sum(d["usage"][k] for d in ds) for k in
                                     ("model_calls", "tool_calls", "input_tokens", "output_tokens")}})
    pairs = []
    for limit in (2, 4):
        for c in conditions[1:]:
            counts = Counter()
            for case in range(12):
                if (case, limit, c) not in trials or (case, limit, "none") not in trials:
                    continue
                a = trials[case, limit, "none"]["evaluation"]["success"]
                b = trials[case, limit, c]["evaluation"]["success"]
                counts["gain" if b and not a else "loss" if a and not b else "same"] += 1
            pairs.append({"source_tool_budget": limit, "condition": c, **counts})
    none_disagreements = [case for case in range(12)
                         if all((case, b, "none") in trials for b in (2, 4))
                         and trials[case, 2, "none"]["evaluation"] != trials[case, 4, "none"]["evaluation"]]
    sources = list(root.glob("shard-*/case-*-source.json"))
    curations = list(root.glob("shard-*/case-*-memory-*.json"))
    source_costs, curation_costs = Counter(), Counter()
    source_outcomes = Counter()
    for p in sources:
        d = json.loads(p.read_bytes())
        source_costs.update(d["usage"])
        source_outcomes[f"budget={d['budget']['tool_calls']};success={d['evaluation']['success']};termination={d['termination']}"] += 1
    for p in curations:
        d = json.loads(p.read_bytes())
        curation_costs.update({k: d["reply"][k] for k in ("input_tokens", "output_tokens")})
        curation_costs["model_calls"] += 1
    missing = sorted(expected - trials.keys())
    return {"purpose": "development_only_not_paper_evidence", "target_grid_complete": not missing,
            "missing_targets": missing, "source_files": len(sources), "expected_source_files": 24,
            "curation_files": len(curations), "expected_curation_files": 48,
            "groups": groups, "paired_vs_none": pairs, "none_evaluation_disagreements": none_disagreements,
            "source_outcomes": dict(source_outcomes), "source_costs": dict(source_costs),
            "curation_costs": dict(curation_costs), "target_file_sha256": hashes,
            "inference_limit": "12 synthetic paired cases; repeated none conditions are not independent samples; no confirmatory significance claim"}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    args = p.parse_args()
    print(json.dumps(summarize(args.root), indent=2))
