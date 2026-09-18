"""Small, task-agnostic experiment loop primitives for autoresearch."""

from .runner import ExperimentRunner, MetricSpec, RunResult

__all__ = ["ExperimentRunner", "MetricSpec", "RunResult"]
