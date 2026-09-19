"""Bounded local-model pilot: matched snapshot tasks, three state-flow conditions.

No reference answers or scoring code are read by this worker.
"""
import argparse
from dataclasses import asdict
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import time

from .hotpot_snapshot import SnapshotWiki
from .local_smoke import sha256_file
from .native_tool_agent import NativeTransformersModel

CONDITIONS = ("baseline", "shared", "isolated")
SETTINGS = {"actor_calls": 8, "actor_new_tokens": 512, "guess_new_tokens": 100,
            "max_input_tokens": 32768, "protocol_error_limit": 3}
SYSTEM = (
    "Answer the question using the provided snapshot search tools. Available article titles "
    "are listed with the question. Search[exact title] returns the first few sentences of "
    "that article; an unknown title returns suggestions. Lookup[keyword] returns the next "
    "matching sentence in the current article. Finish[short answer] ends the task. "
    "Give brief reasoning if needed, then exactly one action on its own line, optionally "
    "prefixed by Action:. Do not give multiple actions. Use Finish for your final answer. "
    "You have at most eight action-generation calls, including malformed responses."
)


def parse_action(text):
    matches = re.findall(r"(?im)^\s*(?:Action(?:\s+\d+)?:\s*)?(Search|Lookup|Finish)\[([^\r\n]*)\]\s*$", text)
    if len(matches) != 1:
        raise ValueError("Return exactly one Search[], Lookup[] or Finish[] action on its own line")
    kind, argument = matches[0]
    if kind.lower() != "finish" and not argument.strip():
        raise ValueError("Search and Lookup require a nonempty argument")
    return kind.lower() + "[" + argument + "]"


def execute_episode(model, item, condition, settings=None):
    if condition not in CONDITIONS:
        raise ValueError("Unknown condition")
    settings = dict(SETTINGS if settings is None else settings)
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content":
        "Question: " + item["question"] + "\nAvailable titles: " + json.dumps([p[0] for p in item["context"]], ensure_ascii=False)}]
    initial_messages = list(messages)
    generations, trace = [], []
    usage = {role: {"attempts": 0, "input_tokens": 0, "output_tokens": 0, "seconds": 0.0}
             for role in ("actor", "prediction")}

    def invoke(role, inputs, limit):
        record = {"role": role, "messages": list(inputs), "max_new_tokens": limit}
        generations.append(record)
        usage[role]["attempts"] += 1
        try:
            reply = model.generate_tools(inputs, [], limit)
            record["reply"] = asdict(reply)
            usage[role]["input_tokens"] += reply.input_tokens
            usage[role]["output_tokens"] += reply.output_tokens
            usage[role]["seconds"] += reply.elapsed_seconds
            return reply.text
        except Exception as exc:
            record.update(error_type=type(exc).__name__, error=str(exc))
            raise

    env = SnapshotWiki(item, lambda prompt: invoke("prediction", [{"role": "user", "content": prompt}], settings["guess_new_tokens"]))
    termination, final, errors = "actor_budget_exhausted", None, 0
    started = time.monotonic()
    for step in range(settings["actor_calls"]):
        event = {"step": step, "state_before": env.state()}
        trace.append(event)
        try:
            text = invoke("actor", messages, settings["actor_new_tokens"])
            event["actor_generation_index"] = len(generations) - 1
            messages.append({"role": "assistant", "content": text})
            try:
                action = parse_action(text)
            except ValueError as exc:
                errors += 1
                event["protocol_error"] = str(exc)
                if errors >= settings["protocol_error_limit"]:
                    termination = "protocol_error_limit"
                    break
                messages.append({"role": "user", "content": str(exc)})
                continue
            event["action"] = action
            observation, reward, done, info = env.step(action)
            event["authoritative_result"] = [observation, reward, done, info]
            event["state_after_authoritative"] = env.state()
            if done:
                final, termination = info["answer"], "finished"
                break
            messages.append({"role": "user", "content": "Observation: " + observation})
            if condition != "baseline":
                event["simulation"] = env.simulate(action, isolate=condition == "isolated")
                event["state_after_simulation"] = env.state()
                if condition == "isolated" and event["state_after_simulation"] != event["state_after_authoritative"]:
                    raise AssertionError("Isolation failed to restore authoritative state")
        except Exception as exc:
            event.update(error_type=type(exc).__name__, error=str(exc), state_at_error=env.state())
            termination = "execution_error"
            break
    return {"id": item["id"], "condition": condition, "settings": settings,
            "initial_messages": initial_messages, "messages": messages,
            "generations": generations, "trace": trace, "usage": usage,
            "protocol_errors": errors, "termination": termination, "final_answer": final,
            "final_state": env.state(), "elapsed_seconds": time.monotonic() - started,
            "scored": False, "native_method_ast_sha256": env.method_hashes}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("inputs", "selection", "model-path", "model-reference", "output"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--shard", type=int, required=True)
    p.add_argument("--shards", type=int, default=2)
    args = p.parse_args()
    selection = json.loads(args.selection.read_bytes())
    assert sha256_file(args.inputs) == selection["groups"]["pilot"]["inputs_sha256"]
    items = json.loads(args.inputs.read_bytes())
    assert len(items) == 8 and [x["id"] for x in items] == selection["groups"]["pilot"]["ids"]
    assert 0 <= args.shard < args.shards == 2
    references = json.loads(args.model_reference.read_bytes())
    files = {p.name: sha256_file(p) for p in sorted(args.model_path.iterdir())
             if p.is_file() and (p.suffix in (".json", ".jinja", ".safetensors") or p.name == "merges.txt")}
    assert files == references["model_files_sha256"], "Model checkpoint differs from pinned prior run"
    args.output.mkdir(parents=True, exist_ok=False)
    source_dir = Path(__file__).parent
    metadata = {"purpose": __doc__, "settings": SETTINGS, "conditions": CONDITIONS,
                "selected_ids": [x["id"] for x in items[args.shard::args.shards]],
                "selection_sha256": sha256_file(args.selection), "inputs_sha256": sha256_file(args.inputs),
                "model_files_sha256": files, "model_reference_sha256": sha256_file(args.model_reference),
                "model_path": str(args.model_path), "shard": args.shard, "shards": args.shards,
                "decoder": "greedy_native_chat_template_empty_tool_list", "seed": 20260919,
                "condition_order": "Rotate baseline/shared/isolated by original pilot index modulo three",
                "packages": {n: importlib.metadata.version(n) for n in ["torch", "transformers", "safetensors", "accelerate"]},
                "source_sha256": {n: sha256_file(source_dir / n) for n in
                    ["hotpot_pilot.py", "hotpot_snapshot.py", "native_tool_agent.py", "local_smoke.py", "tool_agent.py"]}}
    (args.output / "manifest.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    model = NativeTransformersModel(args.model_path, tool_prefix=False, max_input_tokens=SETTINGS["max_input_tokens"])
    placement = dict(model.runtime_placement)
    placement["hf_device_map"] = {k: str(v) for k, v in placement["hf_device_map"].items()}
    (args.output / "model_placement.json").write_text(json.dumps(placement, indent=2), encoding="utf-8")
    for index in range(args.shard, len(items), args.shards):
        order = CONDITIONS[index % 3:] + CONDITIONS[:index % 3]
        for condition in order:
            result = execute_episode(model, items[index], condition)
            with (args.output / f"case-{index:03d}-{condition}.json").open("x", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(json.dumps({"index": index, "condition": condition, "termination": result["termination"]}), flush=True)


if __name__ == "__main__":
    main()
