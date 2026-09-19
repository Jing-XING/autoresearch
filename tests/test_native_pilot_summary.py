import json
from pathlib import Path
import tempfile
import unittest

from autolab.summarize_native_pilot import summarize


class NativePilotSummaryTests(unittest.TestCase):
    def make_trial(self, root, name, limit=2, prompt="same"):
        path = root / "shard-0"
        path.mkdir(exist_ok=True)
        data = {"metadata": {"case": 0, "source_tool_budget": limit, "condition": "none"},
                "evaluation": {"success": False}, "task_sha256": "task", "prompt_sha256": prompt,
                "budget": {"model_calls": 10, "tool_calls": 7, "max_new_tokens": 384},
                "termination": "budget_exhausted", "trace": [],
                "usage": {"model_calls": 1, "tool_calls": 0, "input_tokens": 1, "output_tokens": 1}}
        (path / name).write_text(json.dumps(data))

    def test_partial_results_are_not_complete_or_success_filtered(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.make_trial(root, "case-00-budget-2-target-none.json")
            result = summarize(root)
            self.assertFalse(result["target_grid_complete"])
            self.assertEqual(len(result["missing_targets"]), 95)
            self.assertEqual(result["groups"][0]["n"], 1)
            self.assertEqual(result["groups"][0]["successes"], 0)

    def test_duplicate_metadata_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.make_trial(root, "case-00-target-none.json")
            self.make_trial(root, "case-00-copy-target-none.json")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                summarize(root)

    def test_prompt_changed_across_source_budgets_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.make_trial(root, "case-00-budget-2-target-none.json")
            self.make_trial(root, "case-00-budget-4-target-none.json", 4, "different")
            with self.assertRaisesRegex(ValueError, "prompt_sha256"):
                summarize(root)


if __name__ == "__main__":
    unittest.main()
