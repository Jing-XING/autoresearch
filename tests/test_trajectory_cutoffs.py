import unittest
from autolab.trajectory_cutoffs import make_record, visible_prefix


class TrajectoryCutoffTests(unittest.TestCase):
    def fixture(self):
        messages = [
            {"role": "assistant", "tool_calls": [{"id": "a", "name": "read", "arguments": {}}]},
            {"role": "tool", "id": "a", "content": "observed"},
            {"role": "assistant", "tool_calls": [{"id": "b", "name": "fix", "arguments": {}}]},
            {"role": "tool", "id": "b", "content": "FUTURE_ONLY_CANARY"},
            {"role": "assistant", "content": "###STOP###"},
        ]
        sim = {"task_id": "HIDDEN_TASK_ID", "messages": messages,
               "termination_reason": "agent_stop", "reward_info": {"reward": 1.0}}
        audit = {"task_id": "HIDDEN_TASK_ID", "calls": [{"input": [{"role": "system", "content": "visible ticket"}]}]}
        return sim, audit

    def test_cutoff_has_no_future_or_hidden_task_identity(self):
        sim, audit = self.fixture()
        payload, labels = make_record(sim, audit, 1)
        self.assertNotIn("FUTURE_ONLY_CANARY", str(payload))
        self.assertNotIn("HIDDEN_TASK_ID", str(payload))
        self.assertNotIn("recorded_full_reward", payload)
        self.assertEqual(payload["observed_benchmark_reward"], 0)
        self.assertEqual(payload["stop_reason"], "external_generation_cutoff")
        self.assertTrue(labels["later_recorded_success"])

    def test_cutoff_at_terminal_includes_actual_outcome(self):
        sim, audit = self.fixture()
        payload, labels = make_record(sim, audit, 3)
        self.assertEqual(payload["stop_reason"], "agent_stop")
        self.assertEqual(payload["observed_benchmark_reward"], 1)
        self.assertFalse(labels["unobserved_continuation_exists"])

    def test_multiple_tool_calls_are_an_atomic_observation_group(self):
        messages = [{"role": "assistant", "tool_calls": [
            {"id": "a", "name": "a", "arguments": {}}, {"id": "b", "name": "b", "arguments": {}}]},
            {"role": "tool", "id": "a", "content": "A"}, {"role": "tool", "id": "b", "content": "B"}]
        prefix, generations, complete = visible_prefix(messages, 1)
        self.assertEqual((len(prefix), generations, complete), (3, 1, True))
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            visible_prefix(messages[:-1], 1)


if __name__ == "__main__":
    unittest.main()
