"""Local native-template Agent development runs against official VAKRA MCP.

Only prepared input queries and initialization metadata are read. Evaluation is
offline and separate; this runner has no answer/reference-file argument.
"""
import argparse
import ast
import asyncio
from dataclasses import asdict
from datetime import timedelta
import hashlib
import importlib.metadata
import json
import logging
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace

from .local_smoke import sha256_file
from .native_tool_agent import InputBudgetExceeded, NativeTransformersModel, parse_calls
from .vakra_mcp_audit import decode_result


INSTRUCTION_CONDITIONS = {
    "original": "",
    "coverage_check": (
        "\n\nBefore answering, verify that the observed results cover the requested scope. "
        "A first_3_values preview is a sample, not a complete column. Compare it with num_records. "
        "For a complete list, obtain the relevant full column from a correctly filtered handle. "
        "For a count or aggregate, use the appropriate tool on the correctly filtered data. "
        "Filter or aggregate large tables before fetching full columns. "
        "Check every requested condition, including any status qualifier. "
        "If the evidence remains incomplete, explicitly state that limitation instead of claiming completeness."
    ),
}


def official_system_message(agent_source, peek):
    """Load the unchanged upstream prompt method without optional API clients."""
    tree = ast.parse(agent_source.read_text(encoding="utf-8"))
    methods = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
               and node.name == "_build_system_message"]
    if len(methods) != 1:
        raise ValueError("Expected one upstream prompt method")
    module = ast.Module(body=methods, type_ignores=[])
    namespace = {"json": json, "logger": logging.getLogger(__name__)}
    exec(compile(module, str(agent_source), "exec"), namespace)
    context = SimpleNamespace(_initial_data_handle=peek["handle"], _initial_data_peek=peek)
    return namespace["_build_system_message"](context)


def result_text(result):
    blocks = [item.text for item in result.content if item.type == "text"]
    if not blocks:
        raise ValueError("MCP returned no text content")
    return "\n".join(blocks)


async def run_episode(model, session, query, agent_source, max_steps, max_new_tokens,
                      instruction_condition="original"):
    suffix = INSTRUCTION_CONDITIONS[instruction_condition]
    initial_result = await session.call_tool("get_data", {"tool_universe_id": query["uuid"]})
    peek = decode_result(initial_result)
    tools = [{"type": "function", "function": {
        "name": tool.name, "description": tool.description or "", "parameters": tool.inputSchema}}
        for tool in (await session.list_tools()).tools]
    known = {t["function"]["name"] for t in tools}
    messages = [{"role": "system", "content": official_system_message(agent_source, peek) + suffix},
                {"role": "user", "content": query["dialogue"]["turns"][0]["query"]}]
    usage = {"model_calls": 0, "tool_calls": 0, "input_tokens": 0, "output_tokens": 0,
             "generation_seconds": 0.0, "protocol_errors": 0}
    trace, final_answer, termination = [], None, "max_steps"
    started = time.monotonic()
    for step in range(max_steps):
        event = {"step": step, "input": list(messages)}
        trace.append(event)
        usage["model_calls"] += 1
        try:
            reply = model.generate_tools(messages, tools, max_new_tokens)
        except InputBudgetExceeded as exc:
            event.update(error_type=type(exc).__name__, error=str(exc))
            termination = "input_budget_exceeded"
            break
        except Exception as exc:
            event.update(error_type=type(exc).__name__, error=str(exc))
            termination = "model_error"
            break
        event["reply"] = asdict(reply)
        usage["input_tokens"] += reply.input_tokens
        usage["output_tokens"] += reply.output_tokens
        usage["generation_seconds"] += reply.elapsed_seconds
        messages.append({"role": "assistant", "content": reply.text})
        try:
            calls = parse_calls(reply.text)
            if len(calls) > 1:
                raise ValueError("At most one tool call per iteration is allowed")
            if calls and calls[0]["name"] not in known:
                raise ValueError("Tool name is absent from current schema")
            if not calls and not reply.text.strip():
                raise ValueError("Empty model response")
        except (ValueError, TypeError) as exc:
            event["protocol_error"] = str(exc)
            usage["protocol_errors"] += 1
            if usage["protocol_errors"] >= 5:
                termination = "protocol_error_limit"
                break
            messages.append({"role": "user", "content": "Invalid response: " + str(exc)
                             + ". Use one complete tool_call block with name and arguments, or provide your final answer."})
            continue
        if not calls:
            final_answer = reply.text
            termination = "agent_finished"
            break
        call = calls[0]
        usage["tool_calls"] += 1
        event["tool_call"] = call
        try:
            result = await session.call_tool(call["name"], call["arguments"])
        except Exception as exc:
            event.update(error_type=type(exc).__name__, error=str(exc))
            termination = "transport_error"
            break
        event["tool_result"] = result.model_dump(mode="json")
        messages.append({"role": "tool", "name": call["name"], "tool_call_id": f"native-{step}",
                         "content": result_text(result)})
    return {"uuid": query["uuid"], "query": query, "initial_peek": peek, "tools": tools,
            "trace": trace, "messages": messages, "usage": usage,
            "final_answer": final_answer, "termination": termination,
            "elapsed_seconds": time.monotonic() - started,
            "instruction_condition": instruction_condition}


async def run(args):
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    prepared = args.prepared.resolve()
    prep = json.loads((prepared / "preparation_manifest.json").read_text(encoding="utf-8"))
    for relative, digest in prep["runtime_files"].items():
        if sha256_file(prepared / "runtime" / relative) != digest:
            raise ValueError("Runtime file changed: " + relative)
    database = prepared / (prep["domain"] + ".sqlite")
    if sha256_file(database) != prep["database_sha256"]:
        raise ValueError("Prepared database changed")
    queries = json.loads((prepared / "queries.json").read_text(encoding="utf-8"))
    if sha256_file(prepared / "queries.json") != prep["prepared_queries_sha256"]:
        raise ValueError("Prepared query inputs changed")
    if len(queries) < max(2, args.count):
        raise ValueError("Requested input count unavailable")
    selected = queries[:args.count][args.shard::args.shards]
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "purpose": "public VAKRA capability-1 development, native local model; not default official agent/evaluator",
        "model_path": str(args.model_path), "domain": prep["domain"], "split": prep["split"],
        "all_task_ids": [q["uuid"] for q in queries[:args.count]],
        "selected_task_ids": [q["uuid"] for q in selected],
        "selection": "fixed input order then stride, without outcome filtering",
        "max_steps": args.max_steps, "max_new_tokens": args.max_new_tokens,
        "max_input_tokens": args.max_input_tokens,
        "instruction_condition": args.instruction_condition,
        "instruction_suffix": INSTRUCTION_CONDITIONS[args.instruction_condition],
        "seed": 20260919, "decoder": "greedy_native_template", "supplied_prefix": "",
        "preparation_sha256": sha256_file(prepared / "preparation_manifest.json"),
        "queries_sha256": sha256_file(prepared / "queries.json"),
        "agent_prompt_source_sha256": sha256_file(args.agent_source),
        "source_sha256": {n: sha256_file(Path(__file__).parent / n) for n in
                          ("vakra_native.py", "vakra_stdio.py", "vakra_mcp_audit.py", "native_tool_agent.py", "local_smoke.py")},
        "packages": {n: importlib.metadata.version(n) for n in
                     ("torch", "transformers", "mcp", "pandas", "numpy", "pydantic")},
        "model_files_sha256": {p.name: sha256_file(p) for p in sorted(args.model_path.iterdir())
                                if p.is_file() and (p.suffix in (".json", ".safetensors") or p.name == "merges.txt")},
        "adaptations": ["native Transformers generation replaces hosted LangGraph model",
                        "official system-prompt method loaded without API clients",
                        "initial public MCP switch registers startup getters; refresh schema per query",
                        "five explicit protocol-error retries; no hidden answer evaluation"],
    }
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    model = NativeTransformersModel(args.model_path, tool_prefix=False,
                                    max_input_tokens=args.max_input_tokens)
    params = StdioServerParameters(command=sys.executable,
        args=["-X", "utf8", "-m", "autolab.vakra_stdio", "--runtime", str(prepared / "runtime"),
              "--database", str(database), "--domain", prep["domain"]],
        cwd=str(Path(__file__).resolve().parent.parent),
        env={"PYTHON_DOTENV_DISABLED": "1", "PYTHONUTF8": "1",
             "PYTHONPATH": os.environ.get("PYTHONPATH", "")})
    with (args.output / "server.stderr.log").open("x", encoding="utf-8") as log:
        async with stdio_client(params, errlog=log) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=60)) as session:
                await session.initialize()
                # Prime a universe different from the first selected task.
                # Every evaluated task
                # subsequently begins with a real switch and clean handle store.
                warmup = next(q for q in queries if q["uuid"] != selected[0]["uuid"])
                result = await session.call_tool("get_data", {"tool_universe_id": warmup["uuid"]})
                (args.output / "startup.json").write_text(json.dumps({"uuid": warmup["uuid"],
                    "peek": decode_result(result)}, indent=2), encoding="utf-8")
                for index, query in enumerate(selected):
                    try:
                        episode = await run_episode(model, session, query, args.agent_source,
                                                    args.max_steps, args.max_new_tokens,
                                                    args.instruction_condition)
                    except Exception as exc:
                        episode = {"uuid": query["uuid"], "termination": "run_error",
                                   "error_type": type(exc).__name__, "error": str(exc)}
                    (args.output / f"case-{index:03d}.json").write_text(json.dumps(episode, indent=2, ensure_ascii=False), encoding="utf-8")
                    print(json.dumps({"completed": index + 1, "uuid": query["uuid"],
                                      "termination": episode["termination"]}), flush=True)
    if sha256_file(database) != prep["database_sha256"]:
        raise ValueError("Database changed during agent run")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prepared", type=Path, required=True)
    p.add_argument("--agent-source", type=Path, required=True)
    p.add_argument("--model-path", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--count", type=int, default=4)
    p.add_argument("--shard", type=int, default=0)
    p.add_argument("--shards", type=int, default=1)
    p.add_argument("--max-steps", type=int, default=20)
    p.add_argument("--max-new-tokens", type=int, default=512)
    p.add_argument("--max-input-tokens", type=int)
    p.add_argument("--instruction-condition", choices=tuple(INSTRUCTION_CONDITIONS), default="original")
    args = p.parse_args()
    if not 0 <= args.shard < args.shards or args.count < args.shards or min(args.max_steps, args.max_new_tokens) < 1:
        p.error("Invalid count, shard, or budget")
    if args.max_input_tokens is not None and args.max_input_tokens < 1:
        p.error("Input-token limit must be positive")
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
