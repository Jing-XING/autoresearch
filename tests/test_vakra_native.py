import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from autolab.native_tool_agent import NativeModelReply
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


if __name__ == "__main__":
    unittest.main()
