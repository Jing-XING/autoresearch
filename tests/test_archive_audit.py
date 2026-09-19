import hashlib
import unittest
from autolab.archive_audit import execution_evidence, embedded_integrity


class ArchiveAuditTests(unittest.TestCase):
    def test_kill_is_not_automatically_timeout(self):
        self.assertEqual(execution_evidence({"exit_code": -9}), "killed_reason_unconfirmed")
        record = {"exit_code": -9, "exec_log": {"content": "TIMEOUT after 180s\n"}}
        self.assertEqual(execution_evidence(record), "explicit_timeout")

    def test_missing_evaluation_is_not_a_negative_scientific_result(self):
        self.assertEqual(execution_evidence({"exit_code": 0, "eval_status": "not_run"}),
                         "outcome_unobserved_or_evaluator_not_run")

    def test_failed_execution_cannot_become_pass_from_stale_score(self):
        self.assertEqual(execution_evidence({"exit_code": 1, "eval_status": "ran", "eval_score": 1}),
                         "execution_error")

    def test_nested_artifact_tampering_is_detected(self):
        good = {"content": "abc", "sha256": hashlib.sha256(b"abc").hexdigest()}
        self.assertEqual(embedded_integrity({"inputs": [good]}), [])
        bad = {**good, "content": "abd"}
        self.assertEqual(embedded_integrity({"inputs": [bad]})[0]["field"], "inputs[0]")


if __name__ == "__main__":
    unittest.main()
