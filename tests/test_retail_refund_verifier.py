import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from scripts.verify_retail_refund_interventions_v1 import ROOT, audit

ARCHIVE = ROOT / "results/remote/retail-refund-interventions-v2-results.zip"


@unittest.skipUnless(ARCHIVE.exists(), "Requires retained public experimental artifact")
class VerifierTest(unittest.TestCase):
    def changed_archive(self, mutate):
        with zipfile.ZipFile(ARCHIVE) as z:
            files = {n: z.read(n) for n in z.namelist()}
        rows = [json.loads(x) for x in files["run/records.jsonl"].splitlines()]
        mutate(rows)
        files["run/records.jsonl"] = ("\n".join(json.dumps(r) for r in rows) + "\n").encode()
        report = json.loads(files["run/summary.json"])
        report["output_sha256"]["records.jsonl"] = hashlib.sha256(files["run/records.jsonl"]).hexdigest()
        files["run/summary.json"] = json.dumps(report).encode()
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / "changed.zip"
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            for name, data in files.items():
                z.writestr(name, data)
        return path, hashlib.sha256(path.read_bytes()).hexdigest()

    def test_forged_positive_contract_rejected_despite_consistent_hashes(self):
        def mutate(rows):
            row = next(r for r in rows if r["mode"] == "payment_only" and r["new_payment_method"] is not None)
            row["steps"][-1]["measurement"]["cancellation_contract_met"] = True
        path, digest = self.changed_archive(mutate)
        with self.assertRaisesRegex(ValueError, "Reported contract differs"):
            audit(path, digest)

    def test_changed_gift_effect_rejected_despite_consistent_hashes(self):
        def mutate(rows):
            row = next(r for r in rows if r["mode"] == "net_by_method" and r["new_payment_method"] is not None
                       and r["before"]["payment_methods"][r["old_payment_method"]]["source"] == "gift_card")
            row["steps"][-1]["state"]["payment_methods"][row["old_payment_method"]]["balance"] += 1
        path, digest = self.changed_archive(mutate)
        with self.assertRaisesRegex(ValueError, "Saved cancellation effects differ"):
            audit(path, digest)
