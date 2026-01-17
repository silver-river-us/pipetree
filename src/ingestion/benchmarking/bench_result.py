"""Benchmark result dataclass."""

from dataclasses import dataclass

from ingestion.benchmarking.metrics import Metrics


@dataclass
class BenchResult:
    """Result of a single benchmark run."""

    impl_name: str
    fixture_id: str
    metrics: Metrics
    error: str | None = None
