"""Replay reference programs through VAKRA's real MCP transport and wrappers.

This is a CPU interface compatibility control, never a generated-agent score.
"""
import argparse
import asyncio
from datetime import timedelta
import importlib.metadata
import json
import os
from pathlib import Path
import sys

from .vakra_reference_audit import references, resolve, sha


def decode_result(result):
    texts = [c.text for c in result.content if c.type == "text"]
    if result.isError or len(texts) != 1:
        raise ValueError("MCP error or unexpected content: " + repr(texts))
    try:
        value = json.loads(texts[0])
    except json.JSONDecodeError:
        raise ValueError("Non-JSON tool response: " + texts[0]) from None
    if isinstance(value, dict) and "error" in value:
        raise ValueError(value["error"])
    return value


async def audit(args):
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    prepared = args.prepared.resolve()
    manifest = json.loads((prepared / "preparation_manifest.json").read_text(encoding="utf-8"))
    database = prepared / (manifest["domain"] + ".sqlite")
    if sha(args.references) != manifest["reference_sha256"]:
        raise ValueError("Reference file does not match the prepared runtime")
    before = sha(database)
    records = json.loads(args.references.read_text(encoding="utf-8"))
    queries = json.loads((prepared / "queries.json").read_text(encoding="utf-8"))
    if {r["uuid"] for r in queries} != {r["uuid"] for r in records}:
        raise ValueError("Mismatched runtime/reference pool")
    params = StdioServerParameters(
        command=sys.executable,
        args=["-X", "utf8", "-m", "autolab.vakra_stdio", "--runtime", str(prepared / "runtime"),
              "--database", str(database), "--domain", manifest["domain"]],
        cwd=str(Path(__file__).resolve().parent.parent),
        env={"PYTHON_DOTENV_DISABLED": "1", "PYTHONUTF8": "1",
             "PYTHONPATH": os.environ.get("PYTHONPATH", "")},
    )
    rows = []
    with args.output.with_suffix(".stderr.log").open("x", encoding="utf-8") as log:
        async with stdio_client(params, errlog=log) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=60)) as session:
                init = await session.initialize()
                warmup = None
                if args.warmup:
                    # Upstream Router registers dynamic getter input models
                    # only on a post-construction universe switch. A switch to
                    # another input's universe before the first task triggers
                    # that public code path, without modifying tool behavior.
                    if len(queries) < 2:
                        raise ValueError("Warmup requires two input universes")
                    warmup = decode_result(await session.call_tool("get_data", {"tool_universe_id": queries[1]["uuid"]}))
                for record in records[:args.count]:
                    row = {"uuid": record["uuid"], "trace": []}
                    try:
                        calls = record["output"][0]["sequence"]["tool_call"]
                        if calls[0]["name"] != "initialize_active_data":
                            raise ValueError("Expected reference initialization first")
                        result = await session.call_tool("get_data", {"tool_universe_id": record["uuid"]})
                        initial = decode_result(result)
                        row["initial_peek"] = initial
                        values = {calls[0]["label"]: initial["handle"]}
                        # Dynamic getters can change with initial tables. Refresh
                        # schemas after the official universe switch.
                        tool_list = await session.list_tools()
                        row["tools"] = [t.model_dump(mode="json") for t in tool_list.tools]
                        available = {t.name for t in tool_list.tools}
                        for call in calls[1:]:
                            name = call["name"]
                            if name not in available:
                                raise ValueError("Reference tool absent from MCP schema: " + name)
                            arguments = resolve(call["arguments"], values)
                            renames = {"data": "data_label", "data_1": "data_label_1", "data_2": "data_label_2"}
                            arguments = {renames.get(k, k): v for k, v in arguments.items()}
                            result = await session.call_tool(name, arguments)
                            row["trace"].append({"name": name, "arguments": arguments,
                                                  "result": result.model_dump(mode="json")})
                            value = decode_result(result)
                            values[call["label"]] = value["handle"] if isinstance(value, dict) and "handle" in value else value
                        used = {name for c in calls for name in references(c["arguments"])}
                        terminal = [values[c["label"]] for c in calls if c["label"] not in used]
                        row["actual"] = terminal[0] if len(terminal) == 1 else terminal
                        row["expected"] = record["output"][0]["answer"]
                        row["exact_json_match"] = json.dumps(row["actual"], sort_keys=True) == json.dumps(row["expected"], sort_keys=True)
                    except Exception as exc:
                        row["error_type"] = type(exc).__name__
                        row["error"] = str(exc)
                    rows.append(row)
                    print(json.dumps({"completed": len(rows), "uuid": row["uuid"], "error": row.get("error")}), flush=True)
    if sha(database) != before:
        raise ValueError("Database changed during MCP reference replay")
    report = {
        "purpose": "real MCP reference-program compatibility control; not an agent score",
        "protocol_version": init.protocolVersion,
        "startup_warmup": {"enabled": args.warmup, "peek": warmup},
        "preparation_manifest_sha256": sha(prepared / "preparation_manifest.json"),
        "database_sha256": before,
        "adaptations": ["upstream initialization generator applied to train split",
                        "official server factory without Unix signal-handler shutdown event",
                        "get_data replaces reference initialize_active_data",
                        "reference variables replaced by actual server handles; data arguments renamed per MCP schema",
                        "refresh tool schemas after each universe switch"],
        "packages": {n: importlib.metadata.version(n) for n in ("mcp", "pandas", "numpy", "pydantic", "pyyaml")},
        "n": len(rows), "execution_errors": sum("error" in r for r in rows),
        "exact_matches": sum(r.get("exact_json_match", False) for r in rows), "rows": rows,
    }
    with args.output.open("x", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False)
    print(json.dumps({k: report[k] for k in ("n", "execution_errors", "exact_matches")}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--references", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--count", type=int, default=52)
    parser.add_argument("--warmup", action="store_true", help="Switch to the second input universe before replay")
    args = parser.parse_args()
    if args.count < 1 or args.output.exists():
        raise ValueError("Positive count and new output path required")
    asyncio.run(audit(args))


if __name__ == "__main__":
    main()
