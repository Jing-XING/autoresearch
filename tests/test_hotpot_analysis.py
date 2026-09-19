import copy
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from autolab.hotpot_analysis import same_input_diagnostics, summarize, validate_episode
from autolab.hotpot_pilot import CONDITIONS, SETTINGS, execute_episode
from autolab.hotpot_snapshot import ROOT, load_answer_scorer
from autolab.native_tool_agent import NativeModelReply
from scripts.analyze_hotpot_pilot_v1 import analyze, sha, validate_grid


ITEM = {"id": "fixture", "question": "Use the source", "context": [["Example", ["An authoritative sentence."]]]}


def reply(text):
    # Synthetic IDs, explicitly no tokenizer/model invocation.
    return NativeModelReply(text, 10, len(text), 0.125, text, text, list(text.encode()), "")


class Scripted:
    def __init__(self, prediction_error=False, actor_error=False, malformed=False, empty_prediction=False):
        self.prediction_error = prediction_error
        self.actor_error = actor_error
        self.malformed = malformed
        self.empty_prediction = empty_prediction

    def generate_tools(self, messages, tools, max_new_tokens):
        if messages[0]["role"] == "user":
            if self.prediction_error:
                raise RuntimeError("fixture predictor failure")
            return reply("" if self.empty_prediction else "marker predicted sentence.")
        if self.actor_error:
            raise ValueError("fixture actor failure")
        if self.malformed:
            return reply("Search[Example]\nFinish[wrong]")
        turns = sum(m["role"] == "assistant" for m in messages)
        return reply(["Search[Example]", "Lookup[marker]", "Finish[changed]" if "predicted" in messages[-1]["content"] else "Finish[baseline]"][min(turns, 2)])


class AnalysisTest(unittest.TestCase):
    def test_replay_detects_shared_mutation_and_isolated_restoration(self):
        rows = {c: execute_episode(Scripted(), ITEM, c) for c in CONDITIONS}
        audits = {c: validate_episode(r, ITEM, c) for c, r in rows.items()}
        self.assertEqual(audits["isolated"]["changed_fields"], {})
        self.assertGreater(audits["shared"]["changed_fields"]["page"], 0)
        self.assertEqual(rows["isolated"]["final_answer"], "baseline")
        self.assertEqual(rows["shared"]["final_answer"], "changed")

    def test_failed_generations_and_empty_retry_are_preserved(self):
        for options, termination, calls in [({"prediction_error": True}, "execution_error", 1),
                ({"actor_error": True}, "execution_error", 0),
                ({"malformed": True}, "protocol_error_limit", 0),
                ({"empty_prediction": True}, "finished", 3)]:
            with self.subTest(options=options):
                row = execute_episode(Scripted(**options), ITEM, "isolated")
                validate_episode(row, ITEM, "isolated")
                self.assertEqual(row["termination"], termination)
                self.assertEqual(row["usage"]["prediction"]["attempts"], calls)

    def test_tampered_trace_input_and_usage_rejected(self):
        original = execute_episode(Scripted(), ITEM, "shared")
        for mutate in [lambda r: r["trace"][0]["state_after_simulation"].update(page="forged"),
                       lambda r: r["generations"][0]["messages"][0].update(content="forged"),
                       lambda r: r["generations"][0]["reply"].update(output_tokens=999),
                       lambda r: r["generations"].pop(),
                       lambda r: r["generations"].append(copy.deepcopy(r["generations"][0]))]:
            changed = copy.deepcopy(original)
            mutate(changed)
            with self.assertRaises(ValueError):
                validate_episode(changed, ITEM, "shared")

    def test_same_input_token_disagreement_and_absence_are_not_hidden(self):
        a = execute_episode(Scripted(), ITEM, "baseline")
        b = copy.deepcopy(a)
        b["condition"] = "isolated"
        b["generations"][0]["reply"]["output_token_ids"][0] += 1
        diagnostic = same_input_diagnostics([a, b])
        self.assertEqual(diagnostic["groups_with_token_disagreement"], 1)
        self.assertEqual(diagnostic["groups_with_text_disagreement"], 0)
        errors = [execute_episode(Scripted(actor_error=True), ITEM, c) for c in CONDITIONS]
        diagnostic = same_input_diagnostics(errors)
        self.assertEqual(diagnostic["groups_with_at_least_two_returned"], 0)
        self.assertEqual(diagnostic["groups_with_errors"], 1)


class FullGridTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.archive = ROOT / "results/deploy/hotpot-pilot-v1.zip"
        self.receipt = ROOT / "research/evidence/hotpot_pilot_registration_v1.json"
        with zipfile.ZipFile(self.archive) as z:
            self.registration = json.loads(z.read("protocol/registration.json"))
            self.items = json.loads(z.read("inputs/pilot.json"))
            selection = z.read("research/evidence/hotpot_snapshot_selection_v1.json")
            inputs = z.read("inputs/pilot.json")
            sources = {n: sha(z.read("autolab/" + n)) for n in
                ("hotpot_pilot.py", "hotpot_snapshot.py", "native_tool_agent.py", "local_smoke.py", "tool_agent.py")}
            workers = []
            for model in ("qwen3", "qwen25"):
                reference_bytes = z.read(f"protocol/{model}.json")
                reference = json.loads(reference_bytes)
                for shard in (0, 1):
                    folder = self.root / model / f"shard-{shard}"
                    folder.mkdir(parents=True)
                    manifest = {"settings": SETTINGS, "conditions": list(CONDITIONS),
                        "selected_ids": [i["id"] for i in self.items[shard::2]],
                        "selection_sha256": sha(selection), "inputs_sha256": sha(inputs),
                        "model_files_sha256": reference["model_files_sha256"], "model_reference_sha256": sha(reference_bytes),
                        "shard": shard, "shards": 2, "decoder": "greedy_native_chat_template_empty_tool_list",
                        "seed": 20260919, "condition_order": "Rotate baseline/shared/isolated by original pilot index modulo three",
                        "source_sha256": sources, "packages": {"fixture": True}}
                    self.write(folder / "manifest.json", manifest)
                    self.write(folder / "model_placement.json", {"fixture": True})
                    workers.append({"model": model, "shard": shard, "episodes": 12, "exit_code": 0})
                    for index in range(shard, 8, 2):
                        for condition in CONDITIONS:
                            row = execute_episode(Scripted(actor_error=index == 0 and condition == "isolated"), self.items[index], condition)
                            self.write(folder / f"case-{index:03d}-{condition}.json", row)
        self.grid = {"batch": "hotpot-pilot-v1", "status": "complete", "registered_episodes": 48,
                     "registration": self.registration, "workers": workers}
        self.write(self.root / "grid_manifest.json", self.grid)

    @staticmethod
    def write(path, value):
        path.write_text(json.dumps(value), encoding="utf-8")

    def test_full_grid_and_synthetic_scores(self):
        rows, selection, hashes = validate_grid(self.root, self.archive, self.receipt)
        self.assertEqual(len(rows), 48)
        self.assertEqual(len(hashes), 57)
        # These are invented test labels, not the pilot's sealed gold file.
        gold = [{"_id": i["id"], "answer": "baseline"} for i in self.items]
        report = summarize(rows, gold, load_answer_scorer())
        for model in report["models"].values():
            self.assertEqual(model["conditions"]["baseline"]["em_correct"], 8)
            self.assertEqual(model["conditions"]["isolated"]["em_correct"], 7)
            self.assertEqual(model["conditions"]["isolated"]["terminations"]["execution_error"], 1)
            self.assertEqual(model["paired"][1]["em_losses"], 1)

    def test_incomplete_grid_rejected_before_gold_access(self):
        self.grid["status"] = "running"
        self.write(self.root / "grid_manifest.json", self.grid)
        class NeverRead:
            def read_bytes(self):
                raise AssertionError("Gold accessed before closure")
        with self.assertRaisesRegex(ValueError, "Grid not closed"):
            analyze(self.root, self.archive, self.receipt, NeverRead())

    def test_extra_missing_or_tampered_artifact_rejected(self):
        path = self.root / "qwen3/shard-0/case-000-baseline.json"
        original = path.read_bytes()
        path.unlink()
        with self.assertRaisesRegex(ValueError, "Missing or extra cases"):
            validate_grid(self.root, self.archive, self.receipt)
        path.write_bytes(original)
        extra = path.with_name("case-999-baseline.json")
        extra.write_bytes(original)
        with self.assertRaisesRegex(ValueError, "Missing or extra cases"):
            validate_grid(self.root, self.archive, self.receipt)
        extra.unlink()
        row = json.loads(original)
        row["trace"][0]["state_before"]["steps"] = 100
        self.write(path, row)
        with self.assertRaisesRegex(ValueError, "differs from replay"):
            validate_grid(self.root, self.archive, self.receipt)


if __name__ == "__main__":
    unittest.main()
