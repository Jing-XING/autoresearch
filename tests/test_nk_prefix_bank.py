import copy
import hashlib
import json
import unittest
from pathlib import Path
import tempfile
from unittest.mock import patch

from autolab.nk_prefix_bank import NKMemoryBank, build_bank, validate_outcome
from autolab.nk_prefix_comparator import CONDITIONS, LIMIT, TEXT_LIMITS, VOCABULARIES, prepare
from autolab.nk_prefix_curation import load_prepared


class NKPrefixBankTests(unittest.TestCase):
    def bank(self):
        records = []
        for uid in ("a", "b"):
            records.append({"record_id": uid, "ticket": "identical visible ticket",
                            "memories": {"raw": "raw", **{c: "" if uid == "a" else "lesson" for c in CONDITIONS}},
                            "curation": {c: {"status": "invalid_memory" if uid == "a" else "valid_memory"}
                                         for c in CONDITIONS}})
        return {"schema": "autolab.fixed_experience_bank.v1", "adaptation": "autolab.nk_prefix_bank.v1",
                "source_task_ids": ["training-task"], "records": records}

    def test_invalid_top_source_is_not_replaced_with_valid_tied_source(self):
        bank = NKMemoryBank(self.bank())
        for condition in CONDITIONS:
            selected = bank.retrieve("identical visible ticket", condition)
            self.assertEqual(selected["record_id"], "a")
            self.assertEqual(selected["tied_candidates"], 2)
            self.assertEqual(selected["memory"], "")
            self.assertEqual(selected["curation_status"], "invalid_memory")
            self.assertEqual(selected["memory_sha256"], hashlib.sha256(b"").hexdigest())
        with self.assertRaisesRegex(ValueError, "overlap"):
            bank.assert_disjoint(["training-task"])

    def test_quality_cannot_change_source_selection_between_conditions(self):
        value = self.bank()
        value["records"][0]["memories"][CONDITIONS[1]] = "valid lesson"
        value["records"][0]["curation"][CONDITIONS[1]]["status"] = "valid_memory"
        bank = NKMemoryBank(value)
        a, b = [bank.retrieve("visible ticket", c) for c in CONDITIONS]
        self.assertEqual(a["record_id"], b["record_id"])
        self.assertEqual(a["similarity"], b["similarity"])
        self.assertNotEqual(a["memory"], b["memory"])

    def test_injection_of_invalid_text_rejected(self):
        value = self.bank()
        value["records"][0]["memories"][CONDITIONS[0]] = "partial advice"
        with self.assertRaisesRegex(ValueError, "must not be injected"):
            NKMemoryBank(value)

    def test_output_revalidation_rejects_status_and_input_tampering(self):
        packet = {"record_id": "a", "condition": CONDITIONS[0], "input": [], "input_sha256": "unit"}
        parsed = {"task_id": "a", "failure": {k: v[0] for k, v in VOCABULARIES.items()},
                  **{k: "observed" for k in TEXT_LIMITS}}
        raw = json.dumps(parsed)
        good = {**packet, "status": "valid_memory", "parsed": parsed, "validation_errors": [],
                "reply": {"text": raw, "output_tokens": 200}}
        self.assertEqual(validate_outcome(good, packet), (raw, "valid_memory"))
        altered = copy.deepcopy(good)
        altered["reply"]["text"] = "truncated"
        with self.assertRaisesRegex(ValueError, "validation disagrees"):
            validate_outcome(altered, packet)
        altered = copy.deepcopy(good)
        altered["input"] = [{"role": "user", "content": "future evidence"}]
        with self.assertRaisesRegex(ValueError, "identity changed"):
            validate_outcome(altered, packet)
        failure = {**packet, "status": "generation_error", "error_type": "RuntimeError", "error": "unit"}
        self.assertEqual(validate_outcome(failure, packet), ("", "generation_error"))

    def test_complete_four_shard_assembly_retains_errors_and_rejects_missing_outputs(self):
        # Synthetic CPU assembly fixture; no model inference or performance data.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inputs = root / "inputs"
            inputs.mkdir()
            for uid in ("a", "b", "c", "d"):
                payload = {"system_messages": [{"role": "system", "content": "ticket"}],
                           "observed_messages": [], "generation_budget": 8, "observed_generations": 8,
                           "stop_reason": "external_generation_cutoff", "observed_benchmark_reward": 0}
                (inputs / (uid + ".json")).write_text(json.dumps(payload))
            prepared = root / "prepared"
            prepare(inputs, prepared)
            preparation, packets = load_prepared(prepared)
            model_hashes = {"unit-weights": "unit-hash"}
            code_hashes = {k: "unit-source" for k in
                           ("nk_prefix_curation.py", "nk_prefix_comparator.py", "local_smoke.py", "tool_agent.py")}
            sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
            source_bank = root / "source.json"
            source_bank.write_text(json.dumps({"source_task_ids": ["training"],
                "curation_manifests": [{"configuration": {"model_files_sha256": model_hashes}}],
                "records": [{"record_id": uid, "ticket": "shared ticket", "source_model": "unit",
                             "memories": {"raw": "raw"}} for uid in ("a", "b", "c", "d")]}))
            registration = root / "registration.json"
            registration.write_text(json.dumps({"batch": "nk-prefix-curation-v1",
                "preparation_manifest_sha256": sha(prepared / "manifest.json"),
                "model_files_sha256": model_hashes,
                "source_files_sha256": {"autolab/" + k: v for k, v in code_hashes.items()}}))
            curation = root / "curation"
            for shard, uid in enumerate(("a", "b", "c", "d")):
                folder = curation / f"shard-{shard}"
                folder.mkdir(parents=True)
                manifest = {"schema": "autolab.nk_prefix_curation.v1", "shard": shard, "shards": 4,
                    "preparation": preparation, "preparation_manifest_sha256": sha(prepared / "manifest.json"),
                    "model_files_sha256": model_hashes, "source_sha256": code_hashes, "packages": {},
                    "decoding": "greedy", "seed": 20260919, "max_new_tokens": LIMIT,
                    "selected_record_ids": [uid]}
                (folder / "manifest.json").write_text(json.dumps(manifest))
                rows = []
                for condition in CONDITIONS:
                    value = {**packets[(uid, condition)], "status": "generation_error", "error_type": "UnitError"}
                    (folder / f"{uid}-{condition}.json").write_text(json.dumps(value))
                    rows.append({"record_id": uid, "condition": condition, "status": "generation_error"})
                (folder / "summary.json").write_text(json.dumps({"rows": rows, "expected_records": 2}))
            with patch("autolab.nk_prefix_bank.SOURCE_BANK_SHA", sha(source_bank)):
                bank = build_bank(prepared, curation, source_bank, registration)
                self.assertEqual(len(bank["records"]), 4)
                self.assertEqual(NKMemoryBank(bank).retrieve("shared ticket", CONDITIONS[0])["record_id"], "a")
                self.assertTrue(all(r["memories"][c] == "" for r in bank["records"] for c in CONDITIONS))
                (curation / "shard-3/d-nk_schema.json").unlink()
                with self.assertRaises(FileNotFoundError):
                    build_bank(prepared, curation, source_bank, registration)


if __name__ == "__main__":
    unittest.main()
