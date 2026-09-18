import sys
import tempfile
import unittest
from pathlib import Path

from autolab.runner import ExperimentRunner, MetricSpec


class RunnerTests(unittest.TestCase):
    def _runner(self, root: Path, score: str) -> ExperimentRunner:
        command = f'{sys.executable} -c "print(\\\'score: {score}\\\')"'
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
                command=f'{sys.executable} -c "print(\\\'nothing\\\')"',
                metrics=[MetricSpec("score", r"^score:\s+([0-9.]+)$")],
                log_dir=root / "runs",
                results_file=root / "results.jsonl",
            ).run("missing")
            self.assertEqual(result.status, "crash")
            self.assertIn("missing metrics", result.error)


if __name__ == "__main__":
    unittest.main()
