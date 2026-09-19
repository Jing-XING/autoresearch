import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from autolab.summarize_tau2_native import summarize


class TauSummaryTests(unittest.TestCase):
    def fixture(self, root, model="qwen3", reward=None):
        path = root / model / "shard-0"
        path.mkdir(parents=True)
        manifest = {k: "fixed" for k in ("seed", "decoder", "max_new_tokens", "max_steps", "max_errors",
                     "tau_commit", "tau_source_manifest_sha256", "source_sha256", "task_split")}
        manifest.update(all_task_ids=["a", "b"], selected_task_ids=["a"], model_files_sha256={"weight": "hash"})
        (path / "manifest.json").write_text(json.dumps(manifest))
        (path / "config.json").write_text(json.dumps({"llm_agent": model}))
        (path / "case-000-status.json").write_text(json.dumps({"task_id": "a", "reward": reward, "model_calls": 1}))
        audit = {"task_id": "a", "calls": [{"input": [], "input_sha256": hashlib.sha256(b"[]").hexdigest(),
                  "reply": {"input_tokens": 5, "output_tokens": 2, "elapsed_seconds": 1}, "protocol_error": "no call"}]}
        (path / "case-000-model-audit.json").write_text(json.dumps(audit))
        return path

    def test_failure_and_missing_model_do_not_disappear(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            result = summarize(root)
            self.assertFalse(result["complete"])
            self.assertEqual(result["missing_models"], ["qwen25"])
            group = result["groups"][0]
            self.assertEqual((group["expected_n"], group["completed_n"], group["run_errors"]), (2, 1, 1))
            self.assertEqual(group["protocol_error_runs"], 1)
            self.assertEqual(group["missing_task_ids"], ["b"])

    def test_tampered_model_input_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self.fixture(root) / "case-000-model-audit.json"
            data = json.loads(path.read_text())
            data["calls"][0]["input"] = [{"role": "user", "content": "changed"}]
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                summarize(root)

    def test_incompatible_shards_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            path = self.fixture(root, "qwen25") / "manifest.json"
            data = json.loads(path.read_text())
            data["max_steps"] = "different"
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "Incompatible"):
                summarize(root)
