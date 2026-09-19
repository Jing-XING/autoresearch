"""Replay public VAKRA reference tool sequences as a CPU compatibility audit.

Not a model experiment, not the VAKRA LLM-judge score, and not a new benchmark.
Only a recorded database path is relocated. The official tool implementations
are loaded unmodified with IO wrappers disabled for in-process reference replay.
"""
import argparse
import copy
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def references(value):
    if isinstance(value, str) and value.startswith("$") and value.endswith("$"):
        return [value[1:-1].split(".", 1)[0]]
    if isinstance(value, dict):
        return [x for v in value.values() for x in references(v)]
    if isinstance(value, list):
        return [x for v in value for x in references(v)]
    return []


def resolve(value, values):
    if isinstance(value, str) and value.startswith("$") and value.endswith("$"):
        parts = value[1:-1].split(".", 1)
        result = values[parts[0]]
        return result[parts[1]] if len(parts) == 2 else result
    if isinstance(value, dict):
        return {k: resolve(v, values) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve(v, values) for v in value]
    return value


def replay(record, database, normalization=None):
    from environment.m3.python_tools.tools.sql_tools import initialize_active_data
    from environment.m3.python_tools.tools.tool_registry import SelectionTools
    from environment.m3.python_tools.tools.dtype_utils import DTYPE_METADATA_KEY

    turns = record["output"]
    if len(turns) != 1:
        raise ValueError("This reference audit only supports single-turn capability 1")
    calls = turns[0]["sequence"]["tool_call"]
    if not calls or calls[0]["name"] != "initialize_active_data":
        raise ValueError("Expected reference initialization first")
    initial_args = copy.deepcopy(calls[0]["arguments"])
    initial_args["database_path"] = str(database.resolve())
    initial = initialize_active_data(**initial_args)
    schema = [{"key_name": k, "description": "Reference-replay column " + k, "dtype": "object"}
              for k in initial if k != DTYPE_METADATA_KEY]
    toolbox = SelectionTools(use_io_wrappers=False, use_pydantic_signatures=False).get_toolbox_with_schema(schema)
    values = {calls[0]["label"]: initial}
    trace = [{"tool": calls[0]["name"], "label": calls[0]["label"], "status": "executed"}]
    for call in calls[1:]:
        if call["name"] == "initialize_active_data":
            raise ValueError("Unexpected secondary database initialization")
        args = resolve(call["arguments"], values)
        values[call["label"]] = toolbox[call["name"]](**args)
        trace.append({"tool": call["name"], "label": call["label"], "status": "executed"})
    used = {name for c in calls for name in references(c["arguments"])}
    terminal = [values[c["label"]] for c in calls if c["label"] not in used]
    actual = terminal[0] if len(terminal) == 1 else terminal
    expected = turns[0]["answer"]
    # Record exact JSON equality. No permissive set comparison or silent
    # singleton flattening is used to make an incompatible reference pass.
    actual_json = json.dumps(actual, sort_keys=True, ensure_ascii=False, allow_nan=False)
    expected_json = json.dumps(expected, sort_keys=True, ensure_ascii=False, allow_nan=False)
    result = {"uuid": record["uuid"], "calls": len(calls), "trace": trace,
            "actual": json.loads(actual_json), "expected": expected,
            "exact_json_match": actual_json == expected_json}
    if normalization is not None:
        normalized = [normalization.simplify_and_check_serialization(v) for v in terminal]
        normalized = normalized[0] if len(normalized) == 1 else normalized
        result["live_api_normalized_output"] = normalized
        result["live_api_reference_match"] = normalization.check_equality_without_order(expected, normalized)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--references", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--normalization-source", type=Path, help="Optional official Live API-Bench repository")
    parser.add_argument("--dependency-dir", type=Path, help="Optional isolated dependency installation")
    args = parser.parse_args()
    sys.path.insert(0, str(args.source.resolve()))
    normalization = None
    if args.dependency_dir:
        sys.path.insert(0, str(args.dependency_dir.resolve()))
    if args.normalization_source:
        sys.path.insert(0, str(args.normalization_source.resolve()))
        from live_api_bench.python_tools import execution_helpers as normalization
    records = json.loads(args.references.read_bytes())
    before = sha(args.database)
    rows = []
    for record in records:
        try:
            rows.append(replay(record, args.database, normalization))
        except Exception as exc:
            rows.append({"uuid": record["uuid"], "error_type": type(exc).__name__, "error": str(exc)})
    if sha(args.database) != before:
        raise ValueError("Reference replay modified the database")
    code_root = args.source / "environment/m3/python_tools/tools"
    report = {"purpose": "reference sequence CPU compatibility audit, not agent or official benchmark score",
              "adaptations": ["relocate recorded database path", "disable IO/pydantic wrappers for direct reference replay",
                              "generate getter descriptions from initialized columns; no model consumes these descriptions"],
              "database_sha256": before, "reference_sha256": sha(args.references),
              "official_tool_source_sha256": {p.name: sha(p) for p in sorted(code_root.glob("*.py"))},
              "packages": {n: importlib.metadata.version(n) for n in ("pandas", "numpy", "pydantic")},
              "rows": rows, "n": len(rows),
              "exact_matches": sum(r.get("exact_json_match", False) for r in rows),
              "execution_errors": sum("error" in r for r in rows)}
    if normalization is not None:
        report["live_api_reference_matches"] = sum(r.get("live_api_reference_match", False) for r in rows)
        report["normalization_source_sha256"] = sha(Path(normalization.__file__))
        report["packages"]["sqlglot"] = importlib.metadata.version("sqlglot")
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(json.dumps({k: report[k] for k in ("n", "exact_matches", "execution_errors", "database_sha256",
                                          "live_api_reference_matches") if k in report}))


if __name__ == "__main__":
    main()
