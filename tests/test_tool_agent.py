import json
from pathlib import Path
import tempfile
import unittest

from autolab.tool_agent import Budget, ModelReply, InventorySmokeEnvironment, run_episode, write_episode


class ScriptedModel:
    def __init__(self, actions):
        self.actions = iter(actions)

    def generate(self, messages, max_new_tokens):
        return ModelReply(json.dumps(next(self.actions)), 10, 5, 0.01)


def tool(name, **arguments):
    return {"action": "tool", "name": name, "arguments": arguments}


class ToolAgentTests(unittest.TestCase):
    def test_model_claim_cannot_create_success(self):
        result = run_episode(ScriptedModel([{"action": "finish", "answer": "success: true"}]),
                             InventorySmokeEnvironment(), "Move 2 units", Budget(), {})
        self.assertEqual(result["termination"], "agent_finished")
        self.assertFalse(result["evaluation"]["success"])

    def test_cutoff_does_not_execute_next_tool(self):
        env = InventorySmokeEnvironment()
        result = run_episode(ScriptedModel([tool("prepare_move", quantity=2),
                                           tool("commit_move", receipt="move-1")]),
                             env, "Move 2 units", Budget(tool_calls=1), {})
        self.assertEqual(result["termination"], "budget_exhausted")
        self.assertEqual(result["usage"]["tool_calls"], 1)
        self.assertEqual(env.stock["warehouse_a"], 7)
        self.assertFalse(result["evaluation"]["success"])

    def test_registered_actions_and_separate_score(self):
        result = run_episode(ScriptedModel([
            tool("prepare_move", quantity=2), tool("commit_move", receipt="move-1"),
            {"action": "finish", "answer": "done"}]),
            InventorySmokeEnvironment(), "Move 2 units", Budget(), {})
        self.assertTrue(result["evaluation"]["success"])
        self.assertEqual(result["usage"]["model_calls"], 3)
        self.assertEqual(result["usage"]["output_tokens"], 15)

    def test_generated_shell_is_not_executed(self):
        result = run_episode(ScriptedModel([
            tool("shell", command="arbitrary command"), {"action": "finish"}]),
            InventorySmokeEnvironment(), "Move 2 units", Budget(), {})
        self.assertEqual(result["trace"][0]["observation"]["error"], "unknown_tool")
        self.assertFalse(result["evaluation"]["success"])

    def test_artifacts_cannot_be_silently_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_episode({"success": False}, Path(tmp), "trial-1")
            with self.assertRaises(FileExistsError):
                write_episode({"success": True}, Path(tmp), "trial-1")
            with self.assertRaises(ValueError):
                write_episode({}, Path(tmp), "../escape")


if __name__ == "__main__":
    unittest.main()
