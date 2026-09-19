import copy
import json
from pathlib import Path
import tempfile
import unittest

from autolab.nk_prefix_comparator import (CONDITIONS, LIMIT, TEXT_LIMITS,
    VOCABULARIES, comparator_messages, prepare, validate_reply)


class NKPrefixComparatorTests(unittest.TestCase):
    def fixture(self):
        return {"system_messages": [{"role": "system", "content": "visible policy and ticket"}],
                "observed_messages": [{"role": "tool", "content": "unresolved observation"}],
                "generation_budget": 8, "observed_generations": 8,
                "stop_reason": "external_generation_cutoff", "observed_benchmark_reward": 0.0}

    def valid(self):
        return {"task_id": "id1", "failure": {k: v[0] for k, v in VOCABULARIES.items()},
                **{k: "observed" for k in TEXT_LIMITS}}

    def test_prompt_intervention_preserves_evidence_without_mutation(self):
        payload = self.fixture()
        before = copy.deepcopy(payload)
        a, b = [comparator_messages(payload, "id1", c) for c in CONDITIONS]
        self.assertEqual(a[1], b[1])
        self.assertNotEqual(a[0], b[0])
        self.assertEqual(payload, before)

    def test_hidden_future_fields_and_positive_records_rejected(self):
        for key in ("recorded_full_reward", "future_history", "evaluation_criteria"):
            bad = self.fixture()
            bad[key] = "hidden"
            with self.assertRaisesRegex(ValueError, "Unexpected input fields"):
                comparator_messages(bad, "id1", CONDITIONS[0])
        positive = self.fixture()
        positive["observed_benchmark_reward"] = 1
        with self.assertRaisesRegex(ValueError, "reward zero"):
            comparator_messages(positive, "id1", CONDITIONS[0])

    def test_invalid_outputs_are_retained_as_invalid_without_repair(self):
        valid = self.valid()
        self.assertEqual(validate_reply(json.dumps(valid), "id1", 200), (valid, []))
        self.assertIn("output_ceiling_hit", validate_reply(json.dumps(valid), "id1", LIMIT)[1])
        for field in TEXT_LIMITS:
            bad = self.valid()
            bad[field] = "x" * (TEXT_LIMITS[field] + 1)
            self.assertIn("invalid_text:" + field, validate_reply(json.dumps(bad), "id1", 200)[1])
        bad = self.valid()
        bad["failure"]["degree"] = "certain"
        self.assertIn("invalid_taxonomy:degree", validate_reply(json.dumps(bad), "id1", 200)[1])
        self.assertIn("invalid_json", validate_reply("```json\n{}\n```", "id1", 20)[1])
        self.assertIn("invalid_json", validate_reply('{"task_id":"wrong","task_id":"id1"}', "id1", 20)[1])
        self.assertIn("record_identity_mismatch", validate_reply(json.dumps(valid), "other", 200)[1])

    def test_preparation_does_not_open_sibling_labels_or_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inputs = root / "inputs"
            inputs.mkdir()
            (root / "labels").mkdir()
            (root / "labels" / "secret.json").write_text("invalid JSON should never be read")
            (inputs / "zero.json").write_text(json.dumps(self.fixture()))
            positive = self.fixture()
            positive["observed_benchmark_reward"] = 1
            (inputs / "one.json").write_text(json.dumps(positive))
            manifest = prepare(inputs, root / "prepared")
            self.assertEqual(manifest["selected_record_ids"], ["zero"])
            self.assertEqual(len(manifest["rows"]), 2)
            self.assertEqual(manifest["excluded"], [{"record_id": "one", "reason": "observed_reward_one"}])
            with self.assertRaises(FileExistsError):
                prepare(inputs, root / "prepared")


if __name__ == "__main__":
    unittest.main()
