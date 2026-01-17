"""Backward-compatible re-exports from benchmarking."""

from ingestion.benchmarking import (
    BenchResult,
    BenchRunner,
    Fixture,
    JudgeFn,
    Metrics,
    accuracy_judge,
)

__all__ = [
    "BenchResult",
    "BenchRunner",
    "Fixture",
    "JudgeFn",
    "Metrics",
    "accuracy_judge",
]
