"""Run one bounded experiment and append a machine-readable result.

The agent remains responsible for proposing and committing code changes. This
module makes the repeatable part of the loop deterministic: execute a command,
enforce a timeout, extract metrics, and compare against the best prior run.
It uses only the Python standard library so it can be reused by non-ML tasks.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Literal


Goal = Literal["min", "max"]


@dataclass(frozen=True)
class MetricSpec:
    name: str
    pattern: str
    goal: Goal = "min"


@dataclass
class RunResult:
    run_id: str
    status: str
    command: str | list[str]
    duration_seconds: float
    metrics: dict[str, float]
    best_before: dict[str, float]
    improved: bool
    return_code: int | None
    log_file: str
    error: str = ""


class ExperimentRunner:
    def __init__(
        self,
        command: str | list[str],
        metrics: list[MetricSpec],
        timeout_seconds: int = 600,
        log_dir: str | Path = "runs",
        results_file: str | Path = "results.jsonl",
        cwd: str | Path = ".",
    ) -> None:
        if not metrics:
            raise ValueError("at least one metric is required")
        self.command = command
        self.metrics = metrics
        self.timeout_seconds = timeout_seconds
        self.log_dir = Path(log_dir)
        self.results_file = Path(results_file)
        self.cwd = Path(cwd)

    def _best_before(self) -> dict[str, float]:
        best: dict[str, float] = {}
        if not self.results_file.exists():
            return best
        for line in self.results_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("status") not in {"ok", "keep"}:
                continue
            for spec in self.metrics:
                value = row.get("metrics", {}).get(spec.name)
                if value is None:
                    continue
                if spec.name not in best or self._better(value, best[spec.name], spec.goal):
                    best[spec.name] = value
        return best

    @staticmethod
    def _better(value: float, reference: float, goal: Goal) -> bool:
        return value < reference if goal == "min" else value > reference

    def _extract(self, text: str) -> dict[str, float]:
        values: dict[str, float] = {}
        for spec in self.metrics:
            matches = list(re.finditer(spec.pattern, text, flags=re.MULTILINE))
            if matches:
                values[spec.name] = float(matches[-1].group(1))
        return values

    def run(self, run_id: str) -> RunResult:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        log_path = self.log_dir / f"{run_id}.log"
        best_before = self._best_before()
        started = time.monotonic()
        return_code: int | None = None
        error = ""
        output = ""
        status = "crash"
        try:
            process = subprocess.run(
                # An argv list preserves paths and Python source on Windows.
                # Strings retain the existing POSIX-style CLI syntax.
                shlex.split(self.command) if isinstance(self.command, str) else self.command,
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
            return_code = process.returncode
            output = process.stdout + process.stderr
            if return_code != 0:
                error = f"process exited with code {return_code}"
            else:
                status = "ok"
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode(errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode(errors="replace")
            output = stdout + stderr
            error = f"timeout after {self.timeout_seconds}s"
        except OSError as exc:
            error = str(exc)
        log_path.write_text(output, encoding="utf-8", errors="replace")

        metrics = self._extract(output)
        missing = [spec.name for spec in self.metrics if spec.name not in metrics]
        if status == "ok" and missing:
            status = "crash"
            error = f"missing metrics: {', '.join(missing)}"
        # The first metric is the primary objective. Secondary metrics (such as
        # memory) are reported for constraints and analysis, but cannot turn a
        # worse primary result into an improvement.
        primary = self.metrics[0]
        improved = (
            status == "ok"
            and primary.name in metrics
            and primary.name in best_before
            and self._better(metrics[primary.name], best_before[primary.name], primary.goal)
        )
        result = RunResult(
            run_id=run_id,
            status=status,
            command=self.command,
            duration_seconds=round(time.monotonic() - started, 3),
            metrics=metrics,
            best_before=best_before,
            improved=improved,
            return_code=return_code,
            log_file=str(log_path),
            error=error,
        )
        self.results_file.parent.mkdir(parents=True, exist_ok=True)
        with self.results_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")
        return result


def _parse_metric(value: str) -> MetricSpec:
    # NAME=REGEX[:min|max], where the first capture group is the numeric value.
    name, pattern = value.split("=", 1)
    goal: Goal = "min"
    if pattern.endswith(":max"):
        pattern, goal = pattern[:-4], "max"
    elif pattern.endswith(":min"):
        pattern = pattern[:-4]
    return MetricSpec(name=name, pattern=pattern, goal=goal)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--command", required=True, help="bounded experiment command")
    parser.add_argument("--metric", action="append", required=True, type=_parse_metric, help="NAME=REGEX[:min|max]")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--log-dir", default="runs")
    parser.add_argument("--results", default="results.jsonl")
    parser.add_argument("--cwd", default=".")
    args = parser.parse_args(argv)
    result = ExperimentRunner(
        command=args.command,
        metrics=args.metric,
        timeout_seconds=args.timeout,
        log_dir=args.log_dir,
        results_file=args.results,
        cwd=args.cwd,
    ).run(args.run_id)
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0 if result.status == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
