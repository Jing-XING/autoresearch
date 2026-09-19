import copy
import json
import unittest
from autolab.experience_curator import COMMON_INSTRUCTION, curator_messages


class ExperienceCuratorTests(unittest.TestCase):
    def fixture(self):
        return {"system_messages": [{"role": "system", "content": "ticket"}],
                "observed_messages": [{"role": "tool", "content": "observed result"}],
                "generation_budget": 8, "observed_generations": 8,
                "stop_reason": "external_generation_cutoff", "observed_benchmark_reward": 0.0}

    def test_future_label_injection_is_rejected(self):
        payload = self.fixture()
        payload["recorded_full_reward"] = 1
        with self.assertRaisesRegex(ValueError, "Unexpected input fields"):
            curator_messages(payload, "boundary_aware")

    def test_metadata_intervention_preserves_all_other_evidence(self):
        payload = self.fixture()
        before = copy.deepcopy(payload)
        a = curator_messages(payload, "outcome_only")
        b = curator_messages(payload, "full_metadata")
        self.assertEqual(a[0], b[0])
        a_record, b_record = json.loads(a[1]["content"]), json.loads(b[1]["content"])
        self.assertEqual(b_record.pop("execution_metadata")["stop_reason"], "external_generation_cutoff")
        self.assertEqual(a_record, b_record)
        self.assertEqual(payload, before)

    def test_instruction_intervention_does_not_change_observed_data(self):
        a = curator_messages(self.fixture(), "full_metadata")
        b = curator_messages(self.fixture(), "boundary_aware")
        self.assertEqual(a[1], b[1])
        self.assertEqual(a[0]["content"], COMMON_INSTRUCTION)
        self.assertTrue(b[0]["content"].startswith(COMMON_INSTRUCTION))


if __name__ == "__main__":
    unittest.main()
