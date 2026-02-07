"""Business logic for benchmark results."""

import logging
import os
from pathlib import Path
from typing import Any

from pipetree.infrastructure.progress.benchmark_store import BenchmarkStore

from lib.exceptions import BenchmarkNotFoundError, DatabaseNotFoundError

logger = logging.getLogger(__name__)


def _get_store(db_path: Path) -> BenchmarkStore:
    """Get a BenchmarkStore instance. Raises DatabaseNotFoundError."""
    if not db_path.is_file():
        raise DatabaseNotFoundError(str(db_path))

    return BenchmarkStore(db_path)


def get_all_benchmarks(
    db_path: Path, databases: list[dict] | None = None
) -> list[dict]:
    """Fetch all benchmarks across databases."""
    all_benchmarks: list[dict] = []
    db_sources = _collect_db_sources(db_path, databases)

    for db_file, db_name in db_sources:
        try:
            all_benchmarks.extend(_fetch_benchmarks_from_db(db_file, db_name))
        except Exception:
            logger.debug("Failed to query %s", db_file, exc_info=True)

    all_benchmarks.sort(key=lambda b: b.get("created_at") or 0, reverse=True)
    return all_benchmarks


def get_benchmark_detail(benchmark_id: str, db_path: Path) -> dict[str, Any]:
    """Get benchmark with results, summary, and implementations.

    Returns dict with benchmark, results, summary, implementations, cpu_count.
    Raises DatabaseNotFoundError, BenchmarkNotFoundError.
    """
    store = _get_store(db_path)

    try:
        benchmark = store.get_benchmark(benchmark_id)

        if not benchmark:
            raise BenchmarkNotFoundError(benchmark_id)

        results = store.get_results(benchmark_id)
        summary = store.get_summary(benchmark_id)
        implementations = store.get_implementations(benchmark_id)
    finally:
        store.close()

    return {
        "benchmark": benchmark,
        "results": results,
        "summary": summary,
        "implementations": implementations,
        "cpu_count": os.cpu_count() or 1,
    }


def get_comparison_data(benchmark_id: str, db_path: Path) -> dict[str, Any]:
    """Get data formatted for comparison charts.

    Raises DatabaseNotFoundError, BenchmarkNotFoundError.
    """
    store = _get_store(db_path)

    try:
        benchmark = store.get_benchmark(benchmark_id)

        if not benchmark:
            raise BenchmarkNotFoundError(benchmark_id)

        results = store.get_results(benchmark_id)
        summary = store.get_summary(benchmark_id)
        implementations = store.get_implementations(benchmark_id)
    finally:
        store.close()

    by_fixture = _group_results_by_fixture(results)
    fixtures = list(by_fixture.keys())

    return {
        "benchmark": benchmark,
        "fixtures": fixtures,
        "implementations": implementations,
        "time_data": _extract_metric(by_fixture, fixtures, implementations, "wall_time_s"),
        "memory_data": _extract_metric(by_fixture, fixtures, implementations, "peak_mem_mb"),
        "correctness_data": _extract_metric(by_fixture, fixtures, implementations, "correctness"),
        "cpu_data": _extract_metric(by_fixture, fixtures, implementations, "cpu_time_s"),
        "summary": summary,
        "cpu_count": os.cpu_count() or 1,
    }


def delete_benchmark(benchmark_id: str, db_path: Path) -> None:
    """Delete a benchmark.

    Raises DatabaseNotFoundError on missing DB.
    """
    store = _get_store(db_path)

    try:
        store.delete_benchmark(benchmark_id)
    finally:
        store.close()


def _collect_db_sources(
    db_path: Path, databases: list[dict] | None
) -> list[tuple[Path, str]]:
    db_sources: list[tuple[Path, str]] = []
    seen_paths: set[str] = set()

    if databases:
        for db in databases:
            benchmark_db = Path(db["path"]).parent / "benchmarks.db"

            if benchmark_db.is_file() and str(benchmark_db) not in seen_paths:
                db_sources.append((benchmark_db, db["name"]))
                seen_paths.add(str(benchmark_db))

    benchmark_db = db_path.parent / "benchmarks.db"

    if benchmark_db.is_file() and str(benchmark_db) not in seen_paths:
        db_sources.append((benchmark_db, db_path.parent.parent.name))

    return db_sources


def _fetch_benchmarks_from_db(db_file: Path, db_name: str) -> list[dict]:
    store = BenchmarkStore(db_file)

    try:
        benchmarks = store.get_all_benchmarks()

        for bench in benchmarks:
            bench["db_path"] = str(db_file)
            bench["db_name"] = db_name
            summary = store.get_summary(bench["id"])
            bench["summary"] = summary
            bench["impl_count"] = len(summary)
    finally:
        store.close()

    return benchmarks


def _group_results_by_fixture(results: list[dict]) -> dict[str, dict[str, dict]]:
    by_fixture: dict[str, dict[str, dict]] = {}

    for result in results:
        fixture_id = result["fixture_id"]
        impl_name = result["impl_name"]

        if fixture_id not in by_fixture:
            by_fixture[fixture_id] = {}

        by_fixture[fixture_id][impl_name] = result

    return by_fixture


def _extract_metric(
    by_fixture: dict[str, dict[str, dict]],
    fixtures: list[str],
    implementations: list[str],
    metric: str,
) -> dict[str, list]:
    return {
        impl: [
            by_fixture.get(f, {}).get(impl, {}).get(metric, 0)
            for f in fixtures
        ]
        for impl in implementations
    }
