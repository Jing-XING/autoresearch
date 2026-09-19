import unittest
from autolab.hotpot_pilot import execute_episode, parse_action
from autolab.tool_agent import ModelReply


class ScriptedModel:
    def generate_tools(self, messages, tools, max_new_tokens):
        assert tools == []
        if messages[0]["role"] == "user":
            text = "marker predicted sentence."
        else:
            turns = sum(m["role"] == "assistant" for m in messages)
            text = ["Search[Example]", "Lookup[marker]", "Finish[changed]" if "predicted" in messages[-1]["content"] else "Finish[baseline]"][min(turns, 2)]
        return ModelReply(text, 1, 1, 0.0)


class PilotTest(unittest.TestCase):
    def test_paired_flow_preserves_control_and_records_prediction_cost(self):
        item = {"id": "fixture", "question": "Use the source", "context": [["Example", ["An authoritative sentence."]]]}
        rows = {c: execute_episode(ScriptedModel(), item, c) for c in ("baseline", "shared", "isolated")}
        self.assertEqual(rows["baseline"]["final_answer"], "baseline")
        self.assertEqual(rows["shared"]["final_answer"], "changed")
        self.assertEqual(rows["isolated"]["messages"], rows["baseline"]["messages"])
        self.assertEqual(rows["isolated"]["final_state"], rows["baseline"]["final_state"])
        self.assertEqual(rows["baseline"]["usage"]["prediction"]["attempts"], 0)
        self.assertEqual(rows["isolated"]["usage"]["prediction"]["attempts"], 1)

    def test_multiple_actions_are_not_silently_chosen(self):
        with self.assertRaises(ValueError):
            parse_action("Search[A]\nFinish[B]")
        self.assertEqual(parse_action("A short explanation.\nAction 2: Lookup[word]"), "lookup[word]")

    def test_prediction_failure_is_retained(self):
        class FailureModel(ScriptedModel):
            def generate_tools(self, messages, tools, max_new_tokens):
                if messages[0]["role"] == "user":
                    raise RuntimeError("fixture prediction failure")
                return super().generate_tools(messages, tools, max_new_tokens)
        item = {"id": "fixture", "question": "Use the source", "context": [["Example", ["Source."]]]}
        row = execute_episode(FailureModel(), item, "isolated")
        self.assertEqual(row["termination"], "execution_error")
        self.assertEqual(row["trace"][0]["state_at_error"], row["trace"][0]["state_after_authoritative"])
        self.assertIsNone(row["final_answer"])
        self.assertEqual(row["usage"]["prediction"]["attempts"], 1)


if __name__ == "__main__":
    unittest.main()
