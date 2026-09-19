import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from autolab.experience_memory_bank import FixedMemoryBank, build_bank, ticket_from_payload
from autolab.experience_curator import CONDITIONS, curator_messages
from autolab.trajectory_cutoffs import digest


class ExperienceMemoryBankTests(unittest.TestCase):
    def bank(self):
        return {"schema": "autolab.fixed_experience_bank.v1", "source_task_ids": ["source-only"], "records": [
            {"record_id": "b", "ticket": "cannot send picture messages", "memories": {"raw": "B", "full_metadata": "meta B"}},
            {"record_id": "a", "ticket": "mobile internet very slow", "memories": {"raw": "A", "full_metadata": "meta A"}}]}

    def test_condition_does_not_change_retrieval(self):
        bank = FixedMemoryBank(self.bank())
        a, b = [bank.retrieve("internet slow", c) for c in ["raw", "full_metadata"]]
        self.assertEqual(a["record_id"], "a")
        self.assertEqual(a["record_id"], b["record_id"])
        self.assertNotEqual(a["memory"], b["memory"])

    def test_lesson_text_cannot_change_selection(self):
        value = self.bank()
        altered = copy.deepcopy(value)
        altered["records"][0]["memories"]["raw"] = "internet slow " * 100
        a = FixedMemoryBank(value).retrieve("internet slow", "raw")
        b = FixedMemoryBank(altered).retrieve("internet slow", "raw")
        self.assertEqual(a["record_id"], b["record_id"])

    def test_overlap_rejected_and_empty_query_tie_reported(self):
        bank = FixedMemoryBank(self.bank())
        with self.assertRaisesRegex(ValueError, "overlap"):
            bank.assert_disjoint(["source-only"])
        bank.assert_disjoint(["target-only"])
        retrieved = bank.retrieve("987654", "raw")
        self.assertEqual(retrieved["record_id"], "a")
        self.assertEqual(retrieved["tied_candidates"], 2)

    def test_ticket_extraction_excludes_other_policy_text(self):
        payload = {"system_messages": [{"content": "policy <ticket>user request</ticket> policy"}]}
        self.assertEqual(ticket_from_payload(payload), "user request")

    def prepare_compiler_fixture(self, root):
        source, curated = root / "source", root / "curated"
        (source / "inputs").mkdir(parents=True)
        curated.mkdir()
        payload = {"system_messages": [{"role": "system", "content": "<ticket>internet slow</ticket>"}],
                   "observed_messages": [], "generation_budget": 8, "observed_generations": 8,
                   "stop_reason": "external_generation_cutoff", "observed_benchmark_reward": 0}
        (source / "inputs/r.json").write_text(json.dumps(payload), encoding="utf-8")
        (source / "manifest.json").write_text(json.dumps({"records": [{
            "record_id": "r", "cutoff": 8, "cluster_id": "source-only", "model": "fixture",
            "payload_sha256": digest(payload)}]}), encoding="utf-8")
        manifest = {"generation_cutoff": 8, "conditions": list(CONDITIONS),
                    "seed": 1, "decoding": "scripted test", "max_new_tokens": 256,
                    "source_sha256": {}, "model_files_sha256": {}, "selected_record_ids": ["r"]}
        (curated / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        for condition in CONDITIONS:
            messages = curator_messages(payload, condition)
            data = {"record_id": "r", "condition": condition, "status": "generated", "input": messages,
                    "input_sha256": hashlib.sha256(json.dumps(messages, sort_keys=True).encode()).hexdigest(),
                    "reply": {"text": "scripted fixture only", "input_tokens": 10, "output_tokens": 3, "elapsed_seconds": 0}}
            (curated / f"r-{condition}.json").write_text(json.dumps(data), encoding="utf-8")
        return source, curated

    def test_compiler_needs_no_future_label_files_and_rejects_missing_arm(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, curated = self.prepare_compiler_fixture(Path(tmp))
            self.assertFalse((source / "labels").exists())
            bank = build_bank(source, curated)
            self.assertEqual(len(bank["records"]), 1)
            self.assertEqual(bank["source_task_ids"], ["source-only"])
            (curated / "r-full_metadata.json").unlink()
            with self.assertRaises(FileNotFoundError):
                build_bank(source, curated)

    def test_compiler_rejects_changed_visible_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, curated = self.prepare_compiler_fixture(Path(tmp))
            path = source / "inputs/r.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            value["observed_benchmark_reward"] = 1
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                build_bank(source, curated)


if __name__ == "__main__":
    unittest.main()
