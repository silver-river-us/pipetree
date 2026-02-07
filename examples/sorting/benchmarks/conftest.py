"""Pytest fixtures for sorting benchmarks."""

import os
import random
from pathlib import Path

import pytest
from pipetree import BenchmarkStore, Fixture, HTTPBenchmarkStore

DB_PATH = Path(__file__).parent.parent / "db" / "benchmarks.db"


@pytest.fixture
def benchmark_store() -> BenchmarkStore | HTTPBenchmarkStore:
    """Benchmark store: uses HTTP when env vars are set, else local SQLite."""
    api_url = os.environ.get("PIPETREE_HOST")
    api_key = os.environ.get("PIPETREE_API_KEY")

    if api_url and api_key:
        return HTTPBenchmarkStore(base_url=api_url, api_key=api_key)

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return BenchmarkStore(DB_PATH)


@pytest.fixture
def sorting_fixtures() -> list[Fixture]:
    """Generate lists of various sizes to benchmark against."""
    random.seed(42)
    return [
        {"id": "100", "items": random.sample(range(1000), 100)},
        {"id": "1000", "items": random.sample(range(10000), 1000)},
        {"id": "5000", "items": random.sample(range(50000), 5000)},
    ]
