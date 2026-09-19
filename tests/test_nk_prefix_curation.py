import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from autolab.nk_prefix_comparator import CONDITIONS, LIMIT, TEXT_LIMITS, VOCABULARIES, prepare
from autolab.nk_prefix_curation import generate_packet, load_prepared, run_packets
from autolab.tool_agent import ModelReply


class NKPrefixCurationTests(unittest.TestCase):
    def source(self):
        return {"system_messages": [{"role": "system", "content": "visible ticket"}],
                "observed_messages": [], "generation_budget": 8, "observed_generations": 8,
                "stop_reason": "external_generation_cutoff", "observed_benchmark_reward": 0}

    def prepared(self, root):
        inputs = root / "inputs"
        inputs.mkdir()
        (inputs / "one.json").write_text(json.dumps(self.source()))
        prepare(inputs, root / "prepared")
        return root / "prepared"

    def test_changed_prompt_and_missing_grid_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.prepared(Path(tmp))
            manifest, packets = load_prepared(root)
            self.assertEqual(len(packets), 2)
            packet_path = root / manifest["rows"][0]["file"]
            original = packet_path.read_bytes()
            value = json.loads(original)
            value["input"][1]["content"] += "future outcome"
            packet_path.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "prompt changed"):
                load_prepared(root)
            packet_path.write_bytes(original)
            manifest["rows"].pop()
            (root / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "Incomplete"):
                load_prepared(root)

    def test_path_escape_and_comparator_version_change_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.prepared(Path(tmp))
            original = (root / "manifest.json").read_bytes()
            m = json.loads(original)
            m["rows"][0]["file"] = "../outside.json"
            (root / "manifest.json").write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError, "path"):
                load_prepared(root)
            m = json.loads(original)
            m["source_sha256"] = "0" * 64
            (root / "manifest.json").write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError, "source changed"):
                load_prepared(root)

    def test_all_invalid_or_error_outputs_preserved_without_retry(self):
        class Model:
            calls = 0
            def generate(self, messages, budget):
                self.calls += 1
                if self.calls == 1:
                    return ModelReply(text="unfinished", input_tokens=10, output_tokens=LIMIT, elapsed_seconds=1)
                raise RuntimeError("controlled generation failure")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prepared = self.prepared(root)
            _, packets = load_prepared(prepared)
            out = root / "out"
            out.mkdir()
            model = Model()
            with contextlib.redirect_stdout(io.StringIO()):
                report = run_packets(model, packets, ["one"], out)
            self.assertEqual(model.calls, 2)
            self.assertEqual((report["valid"], report["invalid"], report["generation_errors"]), (0, 1, 1))
            self.assertTrue(all((out / f"one-{c}.json").is_file() for c in CONDITIONS))
            first = json.loads((out / "one-nk_schema.json").read_bytes())
            self.assertEqual(first["reply"]["text"], "unfinished")
            self.assertIn("output_ceiling_hit", first["validation_errors"])

    def test_valid_reply_does_not_mutate_or_rewrite_model_text(self):
        value = {"task_id": "one", "failure": {k: v[0] for k, v in VOCABULARIES.items()},
                 **{k: "unknown" for k in TEXT_LIMITS}}
        raw = json.dumps(value, indent=3)
        class Model:
            def generate(self, messages, budget):
                return ModelReply(text=raw, input_tokens=10, output_tokens=100, elapsed_seconds=1)
        packet = {"record_id": "one", "condition": CONDITIONS[0], "input": [], "input_sha256": "unit"}
        result = generate_packet(Model(), packet)
        self.assertEqual(result["status"], "valid_memory")
        self.assertEqual(result["reply"]["text"], raw)
        self.assertEqual(result["parsed"], value)


if __name__ == "__main__":
    unittest.main()
