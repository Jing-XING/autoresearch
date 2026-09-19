import sys
import tempfile
import unittest
from pathlib import Path

from autolab.runner import ExperimentRunner, MetricSpec


class RunnerTests(unittest.TestCase):
    def _runner(self, root: Path, score: str) -> ExperimentRunner:
        command = [sys.executable, "-c", f"print('score: {score}')"]
        return ExperimentRunner(
            command=command,
            metrics=[MetricSpec("score", r"^score:\s+([0-9.]+)$", "min")],
            log_dir=root / "runs",
            results_file=root / "results.jsonl",
        )

    def test_records_metrics_and_detects_improvement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = self._runner(root, "0.5").run("first")
            self.assertEqual(first.status, "ok")
            self.assertFalse(first.improved)
            second = self._runner(root, "0.4").run("second")
            self.assertTrue(second.improved)
            self.assertEqual(len((root / "results.jsonl").read_text().splitlines()), 2)

    def test_missing_metric_is_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = ExperimentRunner(
                command=[sys.executable, "-c", "print('nothing')"],
                metrics=[MetricSpec("score", r"^score:\s+([0-9.]+)$")],
                log_dir=root / "runs",
                results_file=root / "results.jsonl",
            ).run("missing")
            self.assertEqual(result.status, "crash")
            self.assertIn("missing metrics", result.error)

    def test_nonzero_exit_cannot_be_an_improvement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runner = self._runner(root, "0.5")
            runner.run("baseline")
            runner.command = [sys.executable, "-c", "print('score: 0.1'); raise SystemExit(2)"]
            result = runner.run("failed")
            self.assertEqual(result.status, "crash")
            self.assertEqual(result.return_code, 2)
            self.assertFalse(result.improved)

    def test_timeout_preserves_output_and_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runner = self._runner(root, "0.5")
            runner.command = [sys.executable, "-c", "import time; print('started', flush=True); time.sleep(10)"]
            runner.timeout_seconds = 1
            result = runner.run("timeout")
            self.assertEqual(result.status, "crash")
            self.assertIn("timeout", result.error)
            self.assertIn("started", Path(result.log_file).read_text())


if __name__ == "__main__":
    unittest.main()
