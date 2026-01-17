"""Benchmarking framework for correctness and performance evaluation."""

from ingestion.benchmarking.bench_result import BenchResult
from ingestion.benchmarking.bench_runner import BenchRunner
from ingestion.benchmarking.fixture import Fixture
from ingestion.benchmarking.judges import JudgeFn, accuracy_judge
from ingestion.benchmarking.metrics import Metrics

__all__ = [
    "BenchResult",
    "BenchRunner",
    "Fixture",
    "JudgeFn",
    "Metrics",
    "accuracy_judge",
]
