"""Run with the pinned official tau2 editable install; no GPU or API calls.

Scripted outputs test transport and scoring, not model research performance.
"""
import importlib.util
import json
import os
import unittest
from unittest.mock import patch

os.environ["PYTHON_DOTENV_DISABLED"] = "1"
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"

HAS_TAU = importlib.util.find_spec("tau2") is not None


class ScriptedModel:
    def __init__(self, outputs):
        self.outputs = iter(outputs)

    def generate_tools(self, messages, tools, max_new_tokens):
        from autolab.tool_agent import ModelReply
        return ModelReply(next(self.outputs), 1, 1, 0.0)


def call(name, **arguments):
    return "<tool_call>" + json.dumps({"name": name, "arguments": arguments}) + "</tool_call>"


@unittest.skipUnless(HAS_TAU, "Requires pinned official tau2 source environment")
class Tau2NativeIntegrationTests(unittest.TestCase):
    def run_script(self, outputs, task=None):
        from tau2.data_model.simulation import TextRunConfig
        from tau2.evaluator.evaluator import EvaluationType
        from tau2.runner.batch import run_single_task
        from tau2.runner.helpers import get_tasks
        from autolab.tau2_native_agent import register_native_solo

        task = task or get_tasks("telecom", task_split_name="small", num_tasks=1)[0]
        self.assertNotIn("NL_ASSERTION", str(task.evaluation_criteria.reward_basis))
        audit = []
        name = register_native_solo(ScriptedModel(outputs), audit, name="native_" + self._testMethodName)
        config = TextRunConfig(domain="telecom", agent=name, user=name + "_dummy",
                               llm_agent="scripted-test-only", max_steps=8, max_errors=2,
                               enforce_communication_protocol=True, seed=20260919)
        # Fail closed if evaluation accidentally invokes an external judge.
        with patch("litellm.completion", side_effect=AssertionError("Unexpected API call")):
            result = run_single_task(config, task, seed=20260919, evaluation_type=EvaluationType.ALL)
        return result, audit

    def test_premature_done_fails_official_reward(self):
        result, audit = self.run_script([call("done")])
        self.assertEqual(result.reward_info.reward, 0.0)
        self.assertEqual(len(audit), 1)
        self.assertEqual(result.termination_reason.value, "agent_stop")

    def test_scripted_positive_control_passes_official_state_reward(self):
        # The first small task starts with phone roaming disabled. This is an
        # evaluator positive control, deliberately NOT a blind model result.
        result, audit = self.run_script([call("toggle_roaming"), call("done")])
        self.assertEqual(result.reward_info.reward, 1.0)
        self.assertEqual(len(audit), 2)

    def test_read_tool_round_trip_and_no_oracle_leak(self):
        from tau2.runner.helpers import get_tasks
        task = get_tasks("telecom", task_split_name="small", num_tasks=1)[0].model_copy(deep=True)
        marker = "EVALUATOR_ONLY_CANARY_1f49f872"
        task.evaluation_criteria.actions[0].info = marker
        result, audit = self.run_script([call("check_network_status"), call("done")], task)
        self.assertEqual(result.reward_info.reward, 0.0)
        self.assertEqual(len(audit), 2)
        self.assertNotIn(marker, json.dumps(audit))
        messages = audit[1]["input"]
        assistant = next(m for m in messages if m["role"] == "assistant")
        observation = next(m for m in messages if m["role"] == "tool")
        self.assertEqual(assistant["tool_calls"][0]["id"], observation["tool_call_id"])
        self.assertTrue(observation["content"])

    def test_mixed_done_is_rejected_with_raw_output(self):
        from tau2.runner.helpers import get_tasks
        from autolab.tau2_native_agent import NativeSoloAgent
        task = get_tasks("telecom", task_split_name="small", num_tasks=1)[0]
        text = call("check_network_status") + call("done")
        audit = []
        agent = NativeSoloAgent(model=ScriptedModel([text]), audit=audit, tools=[],
                                domain_policy="test", task=task, llm="scripted-test-only")
        with self.assertRaisesRegex(ValueError, "only call"):
            agent.generate_next_message(None, agent.get_init_state())
        self.assertEqual(audit[0]["reply"]["text"], text)
        self.assertIn("protocol_error", audit[0])

    def test_prefix_audit_detects_reversal_and_keeps_official_failure(self):
        from tau2.runner.helpers import get_tasks
        from autolab.tau2_prefix_audit import audit_prefixes
        task = get_tasks("telecom", task_split_name="small", num_tasks=1)[0]
        result, _ = self.run_script([call("toggle_roaming"), call("toggle_roaming"), call("done")], task)
        original = result.model_dump_json()
        with patch("litellm.completion", side_effect=AssertionError("Unexpected API call")):
            audit = audit_prefixes(result, task)
        self.assertEqual([r["state_satisfied"] for r in audit["prefixes"]], [False, True, False, False])
        self.assertEqual(audit["first_satisfied_generation"], 1)
        self.assertEqual(audit["regressions"], [2])
        self.assertEqual(audit["official_reward"], 0)
        self.assertEqual(result.model_dump_json(), original)

    def test_prefix_audit_preserves_budget_failure_after_state_success(self):
        from tau2.runner.helpers import get_tasks
        from autolab.tau2_prefix_audit import audit_prefixes
        task = get_tasks("telecom", task_split_name="small", num_tasks=1)[0]
        # Four calls and their results exhaust the eight-step orchestration
        # budget. The phone is fixed, but the agent has not issued done.
        result, _ = self.run_script([call("toggle_roaming")] + [call("check_network_status")] * 4, task)
        self.assertEqual(result.termination_reason.value, "max_steps")
        self.assertEqual(result.reward_info.reward, 0)
        audit = audit_prefixes(result, task)
        self.assertTrue(audit["final_state_satisfied"])
        self.assertEqual(audit["official_reward"], 0)

    def test_prefix_audit_rejects_incomplete_tool_responses(self):
        from tau2.runner.helpers import get_tasks
        from autolab.tau2_prefix_audit import audit_prefixes
        task = get_tasks("telecom", task_split_name="small", num_tasks=1)[0]
        result, _ = self.run_script([call("toggle_roaming"), call("done")], task)
        broken = result.model_copy(deep=True)
        broken.messages = broken.messages[:1]
        with self.assertRaisesRegex(ValueError, "Incomplete tool-result"):
            audit_prefixes(broken, task)

    def test_memory_wrapper_exposes_only_lesson_and_preserves_policy(self):
        from tau2.runner.helpers import get_tasks
        from autolab.tau2_native_agent import NativeSoloAgent
        task = get_tasks("telecom", task_split_name="small", num_tasks=1)[0]
        selection = {"record_id": "HIDDEN_SOURCE_ID", "memory": "Observe before retrying.",
                     "similarity": 0.7, "condition": "full_metadata"}
        audit = []
        agent = NativeSoloAgent(model=ScriptedModel([call("done")]), audit=audit,
                                tools=[], domain_policy="CURRENT_POLICY_CANARY", task=task,
                                llm="scripted-test-only", memory_selection=selection)
        state = agent.get_init_state()
        text = state.system_messages[0].content
        self.assertIn("CURRENT_POLICY_CANARY", text)
        self.assertIn(task.ticket, text)
        self.assertIn("Observe before retrying.", text)
        self.assertNotIn("HIDDEN_SOURCE_ID", text)
        self.assertNotIn("full_metadata", text)
        agent.generate_next_message(None, state)
        self.assertEqual(audit[0]["memory_selection"]["record_id"], "HIDDEN_SOURCE_ID")
        self.assertNotIn("memory", audit[0]["memory_selection"])


if __name__ == "__main__":
    unittest.main()
