"""Business logic for benchmark results."""

import logging
import os
from pathlib import Path
from typing import Any

from pipetree.infrastructure.progress.benchmark_store import BenchmarkStore

logger = logging.getLogger(__name__)


def _get_store(db_path: Path) -> BenchmarkStore | None:
    """Get a BenchmarkStore instance if the database exists."""

    if db_path.exists():
        try:
            return BenchmarkStore(db_path)
        except Exception:
            logger.debug("Failed to open benchmark store %s", db_path, exc_info=True)
            return None

    return None


def get_all_benchmarks(
    db_path: Path, databases: list[dict] | None = None
) -> list[dict]:
    """Fetch all benchmarks across databases."""
    all_benchmarks: list[dict] = []
    db_sources: list[tuple[Path, str]] = []
    seen_paths: set[str] = set()

    if databases:
        for db in databases:
            db_file = Path(db["path"])
            benchmark_db = db_file.parent / "benchmarks.db"

            if benchmark_db.exists() and str(benchmark_db) not in seen_paths:
                db_sources.append((benchmark_db, db["name"]))
                seen_paths.add(str(benchmark_db))

    benchmark_db = db_path.parent / "benchmarks.db"

    if benchmark_db.exists() and str(benchmark_db) not in seen_paths:
        db_sources.append((benchmark_db, db_path.parent.parent.name))
        seen_paths.add(str(benchmark_db))

    for db_file, db_name in db_sources:
        try:
            store = BenchmarkStore(db_file)
            benchmarks = store.get_all_benchmarks()

            for bench in benchmarks:
                bench["db_path"] = str(db_file)
                bench["db_name"] = db_name
                summary = store.get_summary(bench["id"])
                bench["summary"] = summary
                bench["impl_count"] = len(summary)

            store.close()
            all_benchmarks.extend(benchmarks)
        except Exception:
            logger.debug("Failed to query %s", db_file, exc_info=True)

    all_benchmarks.sort(key=lambda b: b.get("created_at") or 0, reverse=True)
    return all_benchmarks


def get_benchmark_detail(benchmark_id: str, db_path: Path) -> dict[str, Any] | None:
    """Get benchmark with results, summary, and implementations.

    Returns dict with benchmark, results, summary, implementations, cpu_count
    or None if not found.
    """
    store = _get_store(db_path)

    if not store:
        return None

    try:
        benchmark = store.get_benchmark(benchmark_id)

        if not benchmark:
            return None

        results = store.get_results(benchmark_id)
        summary = store.get_summary(benchmark_id)
        implementations = store.get_implementations(benchmark_id)
        store.close()
        return {
            "benchmark": benchmark,
            "results": results,
            "summary": summary,
            "implementations": implementations,
            "cpu_count": os.cpu_count() or 1,
        }
    except Exception:
        logger.debug("Failed to get benchmark %s", benchmark_id, exc_info=True)
        return None


def get_comparison_data(benchmark_id: str, db_path: Path) -> dict[str, Any] | None:
    """Get data formatted for comparison charts.

    Returns dict with chart data or None if not found.
    """
    store = _get_store(db_path)

    if not store:
        return None

    try:
        benchmark = store.get_benchmark(benchmark_id)

        if not benchmark:
            return None

        results = store.get_results(benchmark_id)
        summary = store.get_summary(benchmark_id)
        implementations = store.get_implementations(benchmark_id)
        store.close()
        by_fixture: dict[str, dict[str, dict]] = {}

        for result in results:
            fixture_id = result["fixture_id"]
            impl_name = result["impl_name"]

            if fixture_id not in by_fixture:
                by_fixture[fixture_id] = {}

            by_fixture[fixture_id][impl_name] = result

        fixtures = list(by_fixture.keys())
        time_data = {
            impl: [
                by_fixture.get(f, {}).get(impl, {}).get("wall_time_s", 0)
                for f in fixtures
            ]
            for impl in implementations
        }
        memory_data = {
            impl: [
                by_fixture.get(f, {}).get(impl, {}).get("peak_mem_mb", 0)
                for f in fixtures
            ]
            for impl in implementations
        }
        correctness_data = {
            impl: [
                by_fixture.get(f, {}).get(impl, {}).get("correctness", 0)
                for f in fixtures
            ]
            for impl in implementations
        }
        cpu_data = {
            impl: [
                by_fixture.get(f, {}).get(impl, {}).get("cpu_time_s", 0)
                for f in fixtures
            ]
            for impl in implementations
        }
        return {
            "benchmark": benchmark,
            "fixtures": fixtures,
            "implementations": implementations,
            "time_data": time_data,
            "memory_data": memory_data,
            "correctness_data": correctness_data,
            "cpu_data": cpu_data,
            "summary": summary,
            "cpu_count": os.cpu_count() or 1,
        }
    except Exception:
        logger.debug("Failed to get comparison for %s", benchmark_id, exc_info=True)
        return None


def delete_benchmark(benchmark_id: str, db_path: Path) -> dict[str, Any]:
    """Delete a benchmark.

    Returns dict with success and optional error.
    """
    store = _get_store(db_path)

    if not store:
        return {"success": False, "error": "Database not found"}

    try:
        success = store.delete_benchmark(benchmark_id)
        store.close()
        return {"success": success}
    except Exception as e:
        logger.debug("Failed to delete benchmark %s", benchmark_id, exc_info=True)
        return {"success": False, "error": str(e)}
