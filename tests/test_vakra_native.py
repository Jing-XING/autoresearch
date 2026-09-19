import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from autolab.native_tool_agent import InputBudgetExceeded, NativeModelReply
from autolab.vakra_native import run_episode


class Result:
    def __init__(self, value):
        self.content = [SimpleNamespace(type="text", text=json.dumps(value))]
        self.isError = False

    def model_dump(self, **unused):
        return {"isError": False, "content": [{"type": "text", "text": self.content[0].text}]}


class Session:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        if name == "get_data":
            return Result({"handle": "initial", "num_records": 1, "key_details": []})
        if self.fail:
            raise TimeoutError("transport unavailable")
        return Result(["Anguilla"])

    async def list_tools(self):
        return SimpleNamespace(tools=[SimpleNamespace(name="get_Names", description="names",
                                inputSchema={"type": "object", "properties": {}})])


class Model:
    def __init__(self, outputs):
        self.outputs = iter(outputs)

    def generate_tools(self, messages, tools, max_new_tokens):
        value = next(self.outputs)
        return NativeModelReply(value, 10, 5, 0.1, value, value, [1] * 5, "")


class TestVakraNative(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.source = Path(self.directory.name) / "agent.py"
        self.source.write_text('class Agent:\n    def _build_system_message(self):\n        return "Use " + self._initial_data_handle\n')
        self.query = {"uuid": "query-1", "dialogue": {"turns": [{"query": "Read the names"}]}}
        self.call = '<tool_call>{"name":"get_Names","arguments":{"data_label":"initial"}}</tool_call>'

    async def test_tool_then_final_answer_without_reference_access(self):
        session = Session()
        result = await run_episode(Model([self.call, "Anguilla"]), session, self.query, self.source, 3, 64)
        self.assertEqual(result["termination"], "agent_finished")
        self.assertEqual(result["usage"]["tool_calls"], 1)
        self.assertEqual(result["final_answer"], "Anguilla")
        self.assertEqual(result["trace"][0]["input"][0]["content"], "Use initial")
        self.assertEqual(result["trace"][1]["input"][-1]["content"], '["Anguilla"]')

    async def test_multiple_calls_rejected_before_side_effect(self):
        session = Session()
        result = await run_episode(Model([self.call + self.call, "No answer"]), session, self.query, self.source, 3, 64)
        self.assertEqual(result["usage"]["protocol_errors"], 1)
        self.assertEqual([c[0] for c in session.calls], ["get_data"])

    async def test_transport_failure_preserves_generated_trace(self):
        result = await run_episode(Model([self.call]), Session(fail=True), self.query, self.source, 3, 64)
        self.assertEqual(result["termination"], "transport_error")
        self.assertEqual(result["trace"][0]["reply"]["text"], self.call)
        self.assertEqual(result["trace"][0]["error_type"], "TimeoutError")

    async def test_input_budget_is_distinct_from_model_error(self):
        class LimitedModel:
            def generate_tools(self, *args):
                raise InputBudgetExceeded("registered limit")
        session = Session()
        result = await run_episode(LimitedModel(), session, self.query, self.source, 3, 64)
        self.assertEqual(result["termination"], "input_budget_exceeded")
        self.assertIsNone(result["final_answer"])
        self.assertEqual([c[0] for c in session.calls], ["get_data"])

    async def test_coverage_control_retains_official_prompt_and_query(self):
        session = Session()
        result = await run_episode(Model(["No answer"]), session, self.query, self.source,
                                   3, 64, instruction_condition="coverage_check")
        self.assertTrue(result["trace"][0]["input"][0]["content"].startswith("Use initial\n\n"))
        self.assertEqual(result["trace"][0]["input"][1]["content"], "Read the names")
        self.assertEqual(result["instruction_condition"], "coverage_check")

    async def test_sequential_batch_preserves_order_and_all_observations(self):
        session = Session()
        second = self.call.replace('"initial"', '"later-handle"')
        result = await run_episode(Model([self.call + second, "Answer"]), session,
            self.query, self.source, 3, 64, call_policy="sequential")
        self.assertEqual(session.calls[1:], [
            ("get_Names", {"data_label": "initial"}),
            ("get_Names", {"data_label": "later-handle"})])
        self.assertEqual(result["usage"]["tool_calls"], 2)
        self.assertEqual(result["usage"]["protocol_errors"], 0)
        self.assertEqual(len(result["trace"][0]["calls"]), 2)
        responses = result["trace"][1]["input"][-2:]
        self.assertEqual([r["tool_call_id"] for r in responses], ["native-0-0", "native-0-1"])
        self.assertTrue(all(r["content"] == '["Anguilla"]' for r in responses))

    async def test_unknown_name_rejects_entire_batch_before_execution(self):
        session = Session()
        result = await run_episode(Model([self.call + self.call.replace('get_Names', 'unknown'), "Answer"]),
            session, self.query, self.source, 3, 64, call_policy="sequential")
        self.assertEqual(len(session.calls), 1)
        self.assertEqual(result["usage"]["protocol_errors"], 1)

    async def test_oversized_batch_does_not_partially_spend_budget(self):
        session = Session()
        result = await run_episode(Model([self.call * 3, self.call, "Answer"]), session,
            self.query, self.source, 4, 64, call_policy="sequential", max_tool_calls=2)
        self.assertEqual(result["usage"]["tool_calls"], 1)
        self.assertEqual(result["trace"][0]["tool_budget_rejection"], {"requested": 3, "remaining": 2})
        self.assertEqual(result["usage"]["protocol_errors"], 0)
        self.assertEqual(result["termination"], "agent_finished")

    async def test_spent_tool_budget_still_allows_final_answer(self):
        result = await run_episode(Model([self.call * 2, "Answer"]), Session(),
            self.query, self.source, 3, 64, call_policy="sequential", max_tool_calls=2)
        self.assertEqual(result["final_answer"], "Answer")
        exceeded = await run_episode(Model([self.call * 2, self.call]), Session(),
            self.query, self.source, 3, 64, call_policy="sequential", max_tool_calls=2)
        self.assertEqual(exceeded["termination"], "tool_budget_exceeded")
        self.assertEqual(exceeded["usage"]["tool_calls"], 2)

    async def test_batch_transport_failure_retains_prefix_and_stops_tail(self):
        class FailingSecond(Session):
            async def call_tool(self, name, arguments):
                if name != "get_data" and len(self.calls) == 2:
                    self.calls.append((name, arguments))
                    raise TimeoutError("second call failed")
                return await super().call_tool(name, arguments)
        session = FailingSecond()
        result = await run_episode(Model([self.call * 3]), session, self.query,
            self.source, 3, 64, call_policy="sequential")
        records = result["trace"][0]["calls"]
        self.assertEqual(len(records), 2)
        self.assertIn("tool_result", records[0])
        self.assertEqual(records[1]["error_type"], "TimeoutError")
        self.assertEqual(result["usage"]["tool_calls"], 2)
        self.assertEqual(result["termination"], "transport_error")


if __name__ == "__main__":
    unittest.main()
