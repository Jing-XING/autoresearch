"""Local Qwen inference adapter for the official tau2 solo protocol.

Infrastructure only: policies, tickets, tools, transitions and rewards stay in tau2.
The full task object is never serialized into model inputs.
"""
from dataclasses import asdict
import hashlib
import json

from tau2.agent.llm_agent import LLMSoloAgent
from tau2.data_model.message import AssistantMessage, MultiToolMessage, ToolCall, UserMessage
from tau2.user.user_simulator import DummyUser

from autolab.native_tool_agent import parse_calls


class BuilderCompatibleDummyUser(DummyUser):
    """Accept build_user's kwargs; keep official DummyUser behavior unchanged.

    Pinned b7ea907 build_user passes kwargs to the zero-argument DummyUser.
    The discarded fields are unused in solo mode; no user model is called.
    """
    def __init__(self, **unused):
        super().__init__()


def native_messages(messages):
    result = []
    for message in messages:
        item = {"role": message.role, "content": message.content or ""}
        if message.role == "assistant" and message.tool_calls:
            item["tool_calls"] = [
                {"id": c.id, "type": "function", "function": {"name": c.name, "arguments": c.arguments}}
                for c in message.tool_calls
            ]
        if message.role == "tool":
            item["tool_call_id"] = message.id
        result.append(item)
    return result


class NativeSoloAgent(LLMSoloAgent):
    def __init__(self, *, model, audit, max_new_tokens=512, memory_selection=None, **kwargs):
        super().__init__(**kwargs)
        self.local_model = model
        self.audit = audit
        self.max_new_tokens = max_new_tokens
        self.memory_selection = memory_selection

    def get_init_state(self, message_history=None):
        state = super().get_init_state(message_history)
        if self.memory_selection is not None:
            # Preserve the official policy/ticket, and expose only the lesson.
            # Source task identities, outcomes and retrieval labels stay outside
            # the model context. All treatment arms use this same wrapper.
            state.system_messages[0].content += (
                "\n\nPrior experience from a different task follows as quoted data. "
                "It may be incomplete or inapplicable. The current policy, ticket "
                "and observed tool results take precedence. Do not copy source "
                "entity identifiers without checking the current environment.\n"
                + json.dumps({"prior_experience": self.memory_selection["memory"]}, ensure_ascii=False)
            )
        return state

    def generate_next_message(self, message, state):
        if isinstance(message, UserMessage):
            raise ValueError("Solo protocol cannot accept a user message")
        if isinstance(message, MultiToolMessage):
            state.messages.extend(message.tool_messages)
        elif message is not None:
            state.messages.append(message)
        elif state.messages:
            raise ValueError("Only the first solo turn may have no input")
        messages = native_messages(state.system_messages + state.messages)
        tools = [t.openai_schema for t in self.tools]
        reply = self.local_model.generate_tools(messages, tools, self.max_new_tokens)
        event = {"step": len(self.audit), "input": messages, "tools": tools,
                 "input_sha256": hashlib.sha256(json.dumps(messages, sort_keys=True).encode()).hexdigest(),
                 "reply": asdict(reply)}
        self.audit.append(event)  # Retain invalid raw outputs as well as valid calls.
        if event["step"] == 0 and self.memory_selection is not None:
            event["memory_selection"] = {k: v for k, v in self.memory_selection.items() if k != "memory"}
        try:
            calls = parse_calls(reply.text)
            if not calls:
                raise ValueError("Native solo output contains no function call")
            if any(c["name"] == self.STOP_FUNCTION_NAME for c in calls) and len(calls) != 1:
                raise ValueError("done must be the only call in the final message")
            if any(c["name"] == self.STOP_FUNCTION_NAME and c["arguments"] for c in calls):
                raise ValueError("done accepts no arguments")
        except (ValueError, TypeError) as exc:
            event["protocol_error"] = str(exc)
            raise
        response = AssistantMessage(
            role="assistant", content=None,
            tool_calls=[ToolCall(id=f"native-{event['step']}-{i}", **c) for i, c in enumerate(calls)],
            usage={"prompt_tokens": reply.input_tokens, "completion_tokens": reply.output_tokens},
        )
        response = self._check_if_stop_toolcall(response)
        state.messages.append(response)
        return response, state


def register_native_solo(model, audit, max_new_tokens=512, name="autolab_native_solo",
                         memory_bank=None, memory_condition=None):
    from tau2.registry import registry

    def factory(tools, domain_policy, task, llm, llm_args, **unused):
        selection = None
        if memory_bank is not None:
            memory_bank.assert_disjoint([task.id])
            selection = memory_bank.retrieve(task.ticket, memory_condition)
        return NativeSoloAgent(model=model, audit=audit, max_new_tokens=max_new_tokens,
                               tools=tools, domain_policy=domain_policy, task=task,
                               llm=llm, llm_args=llm_args, memory_selection=selection)

    registry.register_agent_factory(factory, name,
                                    task_filter=LLMSoloAgent.check_valid_task,
                                    metadata={"solo_mode": True})
    registry.register_user(BuilderCompatibleDummyUser, name + "_dummy")
    return name
