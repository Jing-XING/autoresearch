"""Replay six histories of one selected task and run a public-tool cursor control."""
import asyncio
from datetime import timedelta
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autolab.preview_cursor import enumerate_strings
from autolab.vakra_mcp_audit import decode_result


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=True)


def events(record):
    return [c for step in record["trace"] for c in step.get("calls", [])]


async def run_arm(source, prepared, output):
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client
    record = json.loads(source.read_bytes())
    startup_path = source.parent / "startup.json"
    startup = json.loads(startup_path.read_bytes())
    prior = [source.with_name(f"case-{i:03d}.json") for i in range(15)]
    params = StdioServerParameters(command=sys.executable,
        args=["-X", "utf8", "-m", "autolab.vakra_stdio", "--runtime", str(prepared / "runtime"),
              "--database", str(prepared / "cookbook.sqlite"), "--domain", "cookbook"], cwd=str(ROOT),
        env={"PYTHON_DOTENV_DISABLED": "1", "PYTHONUTF8": "1", "PYTHONPATH": str(ROOT)})
    label = source.parent.parent.parent.name + "-" + source.parent.parent.name
    replay_counts = {"prior_episodes": 0, "prior_calls": 0}
    target_prefix, added = [], []
    with (output / (label + ".stderr.log")).open("x", encoding="utf-8") as log:
        async with stdio_client(params, errlog=log) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=60)) as session:
                await session.initialize()
                warm = decode_result(await session.call_tool("get_data", {"tool_universe_id": startup["uuid"]}))
                assert stable(warm) == stable(startup["peek"]), "Warmup mismatch"
                for path in prior:
                    previous = json.loads(path.read_bytes())
                    peek = decode_result(await session.call_tool("get_data", {"tool_universe_id": previous["uuid"]}))
                    assert stable(peek) == stable(previous["initial_peek"]), "Prior initial mismatch"
                    for event in events(previous):
                        call = event["tool_call"]
                        result = (await session.call_tool(call["name"], call["arguments"])).model_dump(mode="json")
                        assert all(stable(result[k]) == stable(event["tool_result"][k]) for k in ("content", "isError")), "Prior response mismatch"
                        replay_counts["prior_calls"] += 1
                    replay_counts["prior_episodes"] += 1
                peek = decode_result(await session.call_tool("get_data", {"tool_universe_id": record["uuid"]}))
                assert stable(peek) == stable(record["initial_peek"]), "Target initial mismatch"
                schemas = [{"type": "function", "function": {"name": t.name, "description": t.description or "", "parameters": t.inputSchema}}
                           for t in (await session.list_tools()).tools]
                assert stable(schemas) == stable(record["tools"]), "Ordered tool schema mismatch"
                selected = None
                for event in events(record):
                    call = event["tool_call"]
                    response = await session.call_tool(call["name"], call["arguments"])
                    result = response.model_dump(mode="json")
                    assert all(stable(result[k]) == stable(event["tool_result"][k]) for k in ("content", "isError")), "Target prefix mismatch"
                    target_prefix.append({"call": call, "result": result})
                    a = call["arguments"]
                    if call["name"] == "filter_data" and a.get("key_name") == "Recipe_cook_min" and a.get("condition") == "equal_to" and a.get("value") == 900:
                        selected = decode_result(response)
                        assert selected["num_records"] == 10
                        break
                assert selected is not None, "Missing selected prefix"

                async def public_call(name, arguments):
                    response = await session.call_tool(name, arguments)
                    value = decode_result(response)
                    added.append({"call": {"name": name, "arguments": arguments}, "result": response.model_dump(mode="json")})
                    return value

                control = await enumerate_strings(public_call, selected["handle"], "Ingredient_name", 20 - len(target_prefix))
    result = {"source": source.relative_to(ROOT).as_posix(), "source_sha256": sha(source),
              "startup_sha256": sha(startup_path), "prior_sha256": {p.name: sha(p) for p in prior},
              "exact_replay": replay_counts, "initial_and_ordered_schemas_match": True,
              "target_prefix": target_prefix, "added_calls": added, "control": control,
              "target_calls_total": len(target_prefix) + len(added),
              "model_continuation": False}
    # Save actual execution before oracle validation, preserving a failed comparison.
    (output / (label + ".json")).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


async def main():
    prepared = ROOT / "results/vakra-domain-expansion-v1/cookbook"
    prep = json.loads((prepared / "preparation_manifest.json").read_bytes())
    database = prepared / "cookbook.sqlite"
    assert sha(database) == prep["database_sha256"]
    for name, digest in prep["runtime_files"].items():
        assert sha(prepared / "runtime" / name) == digest
    output = ROOT / "results/probes/cookbook-acquisition-v1"
    output.mkdir(parents=True, exist_ok=False)
    root = ROOT / "results/remote/vakra-expansion-v2-cookbook-complete/runs/vakra-expansion-v2/cookbook"
    sources = sorted(root.glob("*/*/shard-0/case-015.json"))
    assert len(sources) == 6
    rows = []
    for source in sources:
        rows.append(await run_arm(source, prepared, output))
        print(json.dumps({"arm": str(source.relative_to(root)), "calls": rows[-1]["target_calls_total"], "complete": rows[-1]["control"]["complete"]}), flush=True)
    # Oracle is loaded only after every controller has returned and its log is written.
    cp = ROOT / "research/evidence/vakra_domain_expansion_sql_cards_v1.json"
    card = next(c for c in json.loads(cp.read_bytes())["cards"] if c["domain"] == "cookbook" and c["task_index"] == 15)
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as con:
        sql_rows = [list(row) for row in con.execute(card["sql"]).fetchall()]
    assert sql_rows == card["answer_rows"]
    required = sorted({row[1] for row in sql_rows})
    for row in rows:
        row["matches_frozen_sql"] = row["control"]["values"] == required
    assert sha(database) == prep["database_sha256"]
    report = {"purpose": __doc__, "complete": True, "independent_tasks": 1, "histories": 6,
              "protocol_sha256": sha(ROOT / "research/cookbook_acquisition_control.md"),
              "script_sha256": sha(Path(__file__)), "controller_sha256": sha(ROOT / "autolab/preview_cursor.py"),
              "preparation_sha256": sha(prepared / "preparation_manifest.json"),
              "database_sha256": sha(database), "database_unchanged": True,
              "frozen_cards_sha256": sha(cp), "required_values": required,
              "dependencies": {p: importlib.metadata.version(p) for p in ["mcp", "pandas", "numpy", "pydantic"]},
              "rows": rows,
              "limits": ["Post-outcome evaluator-authored keyset pagination, not a new algorithm or model repair result.",
                         "Correct predicate and output column selected by evaluator; one task with six histories.",
                         "Non-null string, stable-state and matching order assumptions; not a general semantic certificate.",
                         "Warmup and previous independent tasks reproduce interface state, excluded from target twenty-call budget."]}
    path = ROOT / "research/evidence/vakra_cookbook_acquisition_control_v1.json"
    with path.open("x", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    assert all(r["matches_frozen_sql"] and r["control"]["complete"] and r["target_calls_total"] <= 20 for r in rows)
    print(json.dumps({"six_histories": True, "independent_tasks": 1, "all_match_frozen_sql": True}))


if __name__ == "__main__":
    asyncio.run(main())
