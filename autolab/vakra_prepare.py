"""Prepare an isolated VAKRA capability-1 runtime with official initialization.

The original checkout is never edited. The upstream mapping generator reads
reference programs to recover the prescribed initial table/join and tool family;
the runtime receives only that mapping and input queries, never answer/program
files. This is an environment setup step, not a benchmark score.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(source, data, domain, split, output):
    import yaml

    source, data, output = map(lambda p: Path(p).resolve(), (source, data, output))
    if output.exists():
        raise FileExistsError(output)
    if not domain or Path(domain).name != domain or split not in {"train", "test"}:
        raise ValueError("Expected a single domain name and train/test split")
    input_path = data / split / "capability_1_bi_apis/input" / (domain + ".json")
    reference_path = data / split / "capability_1_bi_apis/output" / (domain + ".json")
    inputs = json.loads(input_path.read_text(encoding="utf-8"))
    references = json.loads(reference_path.read_text(encoding="utf-8"))
    ids = [r["uuid"] for r in inputs]
    if len(set(ids)) != len(ids) or set(ids) != {r["uuid"] for r in references}:
        raise ValueError("Duplicate or unpaired query identifiers")
    if any(r["domain"] != domain or r["num_turns"] != 1 for r in inputs):
        raise ValueError("Only single-turn queries in the selected domain are supported")
    output.mkdir(parents=True)
    runtime = output / "runtime"
    # Only the capability-1 Python server is needed. Do not package unrelated
    # BPO fixtures, REST metadata or other benchmark data with the agent runtime.
    for directory in ("environment/m3/python_tools/tools", "environment/m3/python_tools/mcp"):
        shutil.copytree(source / directory, runtime / directory,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for filename in ("environment/__init__.py", "environment/mcp_logging.py",
                     "environment/m3/__init__.py", "environment/m3/python_tools/__init__.py",
                     "environment/configs/generate_task_1_tool_universe_mapping.py"):
        destination = runtime / filename
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / filename, destination)
    for filename in ("LICENSE", "NOTICE"):
        if (source / filename).is_file():
            shutil.copy2(source / filename, runtime / filename)
    mapping_rel = Path("environment/configs/mcp_tool_universe_id_mapping.yaml")
    stock = yaml.safe_load((source / mapping_rel).read_text(encoding="utf-8"))
    generator = source / "environment/configs/generate_task_1_tool_universe_mapping.py"
    spec = importlib.util.spec_from_file_location("upstream_vakra_mapping", generator)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.REPO_ROOT = data
    module.OUTPUT_DIRS_GLOB = split + "/capability_1_bi_apis/output"
    module.MAPPING_FILE = str(runtime / mapping_rel)
    module.generate_mapping()
    generated = yaml.safe_load((runtime / mapping_rel).read_text(encoding="utf-8"))
    mapping = {uid: generated[uid] for uid in ids}
    for query in inputs:
        item = mapping[query["uuid"]]
        if set(item) != {"domain", "server_type", "init_args", "query"}:
            raise ValueError("Unexpected upstream mapping fields")
        if item["domain"] != domain or item["query"] != query["dialogue"]["turns"][0]["query"]:
            raise ValueError("Input/reference query mismatch")
    # The official generator may see other downloaded domains. Retain only the
    # requested input pool, in input order, without any outcome-based filtering.
    (runtime / mapping_rel).write_text(yaml.safe_dump(mapping, sort_keys=False), encoding="utf-8")
    (output / "queries.json").write_text(json.dumps(inputs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    database = data / "databases" / domain / (domain + ".sqlite")
    shutil.copy2(database, output / (domain + ".sqlite"))
    manifest = {
        "kind": "vakra_capability1_runtime_preparation", "split": split, "domain": domain,
        "queries": len(ids), "stock_mapping_overlap": sum(uid in stock for uid in ids),
        "generator_sha256": sha(generator), "input_sha256": sha(input_path),
        "prepared_queries_sha256": sha(output / "queries.json"),
        "reference_sha256": sha(reference_path), "database_sha256": sha(database),
        "mapping_sha256": sha(runtime / mapping_rel),
        "reference_access": "upstream initialization/tool-family derivation only; no reference file copied",
        "source_files": {p.relative_to(runtime).as_posix(): sha(source / p.relative_to(runtime))
                         for p in sorted(runtime.rglob("*")) if p.is_file()},
        "runtime_files": {p.relative_to(runtime).as_posix(): sha(p)
                          for p in sorted(runtime.rglob("*")) if p.is_file()},
    }
    (output / "preparation_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--split", choices=("train", "test"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = prepare(**vars(args))
    print(json.dumps({k: manifest[k] for k in ("queries", "stock_mapping_overlap", "mapping_sha256")}, indent=2))


if __name__ == "__main__":
    main()
