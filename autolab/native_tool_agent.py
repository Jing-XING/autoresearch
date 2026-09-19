"""Explicit native tool-template profiles; infrastructure, not a research method."""
from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json
import re
import time

from autolab.local_smoke import LocalTransformersModel
from autolab.tool_agent import ModelReply


@dataclass
class NativeModelReply(ModelReply):
    completion_text: str
    raw_completion_text: str
    output_token_ids: list[int]
    supplied_prefix: str


class InputBudgetExceeded(ValueError):
    """A registered input-token budget, not an inferred model failure."""


def parse_calls(text):
    blocks = re.findall(r"<tool_call>\s*(.*?)\s*</tool_call>", text, re.S)
    if text.count("<tool_call>") != len(blocks) or text.count("</tool_call>") != len(blocks):
        raise ValueError("Incomplete tool-call block")
    calls = []
    for block in blocks:
        value = json.loads(block)
        if not isinstance(value, dict) or set(value) != {"name", "arguments"}:
            raise ValueError("Expected tool name and arguments")
        if not isinstance(value["name"], str) or not isinstance(value["arguments"], dict):
            raise ValueError("Invalid tool name or arguments")
        calls.append(value)
    return calls


def template_options(tools, profile="standard", template_date="2026-09-19"):
    if profile == "standard":
        return {"tools": tools}
    if profile == "smollm3_no_think":
        date = datetime.strptime(template_date, "%Y-%m-%d")
        return {"xml_tools": [t["function"] for t in tools], "enable_thinking": False,
                "strftime_now": date.strftime}
    raise ValueError("Unsupported native template profile")


class NativeTransformersModel(LocalTransformersModel):
    def __init__(self, model_path, tool_prefix=False, max_input_tokens=None,
                 template_profile="standard", template_date="2026-09-19"):
        template_options([], template_profile, template_date)
        super().__init__(model_path)
        self.tool_prefix = tool_prefix
        self.max_input_tokens = max_input_tokens
        self.template_profile = template_profile
        self.template_date = template_date

    def generate_tools(self, messages, tools, max_new_tokens):
        prefix = "<tool_call>\n" if self.tool_prefix else ""
        options = template_options(tools, self.template_profile, self.template_date)
        if prefix:
            prompt = self.tokenizer.apply_chat_template(
                messages, add_generation_prompt=True, tokenize=False, **options)
            tensors = self.tokenizer(prompt + prefix, add_special_tokens=False,
                                     return_tensors="pt")
        else:
            tensors = self.tokenizer.apply_chat_template(
                messages, add_generation_prompt=True, tokenize=True,
                return_tensors="pt", return_dict=True, **options)
        n_input = tensors["input_ids"].shape[-1]
        limit = self.max_input_tokens
        if limit is not None and n_input > limit:
            raise InputBudgetExceeded(f"Input has {n_input} tokens; registered maximum is {limit}")
        tensors = tensors.to(self.model.device)
        self.torch.cuda.synchronize()
        started = time.monotonic()
        with self.torch.inference_mode():
            result = self.model.generate(**tensors, max_new_tokens=max_new_tokens,
                                         do_sample=False, pad_token_id=self.tokenizer.eos_token_id)
        self.torch.cuda.synchronize()
        output = result[0, n_input:]
        completion = self.tokenizer.decode(output, skip_special_tokens=True)
        return NativeModelReply(prefix + completion, n_input, len(output), time.monotonic() - started,
                                completion, self.tokenizer.decode(output, skip_special_tokens=False),
                                output.tolist(), prefix)


def run_native_episode(model, env, task, budget, metadata, tools, memory=""):
    known = {t["name"] for t in env.tools()}
    if {t["function"]["name"] for t in tools} != known:
        raise ValueError("Native schema must match registered environment tools")
    system = ("Complete the user's task with the provided tools. Tool results are observations. "
              "Do not claim completion until required environment actions have been performed. "
              "Execution limits: " + json.dumps(asdict(budget)))
    user = (("Prior experience, which may not apply:\n" + memory + "\n\n") if memory else "") + task
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    usage = {"model_calls": 0, "tool_calls": 0, "input_tokens": 0, "output_tokens": 0}
    trace = []
    status = "budget_exhausted"
    started = time.monotonic()
    for step in range(budget.model_calls):
        usage["model_calls"] += 1
        try:
            reply = model.generate_tools(messages, tools, budget.max_new_tokens)
        except Exception as exc:
            status = "model_error"
            trace.append({"step": step, "error_type": type(exc).__name__})
            break
        usage["input_tokens"] += reply.input_tokens
        usage["output_tokens"] += reply.output_tokens
        event = {"step": step, "reply": asdict(reply), "calls": []}
        trace.append(event)
        # Keep the exact native text; the official template can serialize it verbatim.
        messages.append({"role": "assistant", "content": reply.text})
        try:
            calls = parse_calls(reply.text)
        except (ValueError, TypeError) as exc:
            event["protocol_error"] = str(exc)
            messages.append({"role": "user", "content": "Malformed function call. Return a complete tool_call block with name and an arguments object."})
            continue
        if not calls:
            status = "agent_finished"
            break
        stopped = False
        for index, call in enumerate(calls):
            if usage["tool_calls"] >= budget.tool_calls:
                event["tool_budget_exhausted"] = True
                stopped = True
                break
            usage["tool_calls"] += 1
            if call["name"] not in known:
                observation = {"error": "unknown_tool"}
            else:
                try:
                    observation = env.execute(call["name"], call["arguments"])
                except Exception as exc:
                    observation = {"error": "tool_exception", "type": type(exc).__name__}
            event["calls"].append({"call": call, "observation": observation})
            messages.append({"role": "tool", "name": call["name"],
                             "tool_call_id": f"call-{step}-{index}", "content": json.dumps(observation)})
        if stopped:
            break
    evaluation = env.evaluate()
    if not isinstance(evaluation.get("success"), bool):
        raise ValueError("Independent evaluator must return a boolean")
    return {"schema": "autolab.native_episode.v1", "metadata": metadata, "budget": asdict(budget),
            "usage": usage, "trace": trace, "messages": messages, "tools": tools,
            "task_sha256": hashlib.sha256(task.encode()).hexdigest(),
            "prompt_sha256": hashlib.sha256((system + json.dumps(tools, sort_keys=True)).encode()).hexdigest(),
            "memory_sha256": hashlib.sha256(memory.encode()).hexdigest(),
            "termination": status, "evaluation": evaluation,
            "duration_seconds": time.monotonic() - started}


SQL_TOOLS = [{"type": "function", "function": {
    "name": name, "description": description, "parameters": {
        "type": "object", "properties": properties, "required": list(properties),
        "additionalProperties": False}}} for name, description, properties in [
    ("schema", "Read the database table schemas and join relationship.", {}),
    ("query", "Execute one read-only SQLite SELECT. Returns at most 30 rows.",
     {"sql": {"type": "string"}}),
    ("submit_answer", "Record the requested integer answer. No correctness feedback is returned.",
     {"value": {"type": "integer"}})]]
