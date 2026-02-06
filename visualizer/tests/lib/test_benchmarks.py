"""Tests for visualizer.lib.benchmarks."""

from pathlib import Path

import pytest
from pipetree.infrastructure.progress.benchmark_store import BenchmarkStore

from unittest.mock import patch

from lib.benchmarks import (
    _get_store,
    delete_benchmark,
    get_all_benchmarks,
    get_benchmark_detail,
    get_comparison_data,
)


@pytest.fixture
def benchmark_db(tmp_path: Path) -> Path:
    """Create a seeded benchmark database."""
    db_file = tmp_path / "benchmarks.db"
    store = BenchmarkStore(db_file)
    bid = store.create_benchmark(
        name="sort_test",
        capability="sorting",
        description="Sort benchmark",
    )
    store.add_result(
        benchmark_id=bid,
        impl_name="quicksort",
        fixture_id="small",
        wall_time_s=0.5,
        cpu_time_s=0.4,
        peak_mem_mb=10.0,
        correctness=1.0,
    )
    store.add_result(
        benchmark_id=bid,
        impl_name="mergesort",
        fixture_id="small",
        wall_time_s=0.6,
        cpu_time_s=0.5,
        peak_mem_mb=12.0,
        correctness=1.0,
    )
    store.add_result(
        benchmark_id=bid,
        impl_name="quicksort",
        fixture_id="large",
        wall_time_s=2.0,
        cpu_time_s=1.8,
        peak_mem_mb=50.0,
        correctness=1.0,
    )
    store.add_result(
        benchmark_id=bid,
        impl_name="mergesort",
        fixture_id="large",
        wall_time_s=1.5,
        cpu_time_s=1.3,
        peak_mem_mb=60.0,
        correctness=1.0,
    )
    store.complete_benchmark(bid)
    store.close()
    return tmp_path


class TestGetStore:
    def test_nonexistent_path(self, tmp_path: Path) -> None:
        assert _get_store(tmp_path / "nope.db") is None

    def test_existing_path(self, benchmark_db: Path) -> None:
        store = _get_store(benchmark_db / "benchmarks.db")
        assert store is not None
        store.close()

    def test_corrupted_file(self, tmp_path: Path) -> None:
        bad = tmp_path / "corrupt.db"
        bad.write_text("not a database")
        # BenchmarkStore init may or may not raise; _get_store catches it
        result = _get_store(bad)
        # Either returns None or a store (SQLite is lenient with file content)
        if result is not None:
            result.close()


class TestGetAllBenchmarks:
    def test_returns_benchmarks(self, benchmark_db: Path) -> None:
        db_path = benchmark_db / "benchmarks.db"
        result = get_all_benchmarks(db_path)
        assert len(result) == 1
        assert result[0]["name"] == "sort_test"
        assert result[0]["impl_count"] == 2

    def test_nonexistent_db(self, tmp_path: Path) -> None:
        result = get_all_benchmarks(tmp_path / "nope.db")
        assert result == []

    def test_with_databases_list(self, benchmark_db: Path) -> None:
        # databases list points to the parent dir where benchmarks.db lives
        db_path = benchmark_db / "progress.db"
        databases = [{"path": str(db_path), "name": "test"}]
        result = get_all_benchmarks(db_path, databases=databases)
        assert len(result) == 1

    def test_exception_in_store(self, tmp_path: Path) -> None:
        """Cover except block in get_all_benchmarks."""
        db_path = tmp_path / "benchmarks.db"
        db_path.write_text("not a db")
        result = get_all_benchmarks(db_path)
        assert result == []


class TestGetBenchmarkDetail:
    def test_returns_detail(self, benchmark_db: Path) -> None:
        db_path = benchmark_db / "benchmarks.db"
        benchmarks = get_all_benchmarks(db_path)
        bid = benchmarks[0]["id"]

        result = get_benchmark_detail(bid, db_path)
        assert result is not None
        assert result["benchmark"]["name"] == "sort_test"
        assert len(result["results"]) == 4
        assert len(result["implementations"]) == 2
        assert result["cpu_count"] >= 1

    def test_nonexistent_benchmark(self, benchmark_db: Path) -> None:
        db_path = benchmark_db / "benchmarks.db"
        result = get_benchmark_detail("no-such-id", db_path)
        assert result is None

    def test_nonexistent_db(self, tmp_path: Path) -> None:
        result = get_benchmark_detail("x", tmp_path / "nope.db")
        assert result is None

    def test_exception_in_store(self, benchmark_db: Path) -> None:
        """Cover except block in get_benchmark_detail."""
        db_path = benchmark_db / "benchmarks.db"
        with patch(
            "lib.benchmarks.BenchmarkStore.get_benchmark",
            side_effect=RuntimeError("boom"),
        ):
            result = get_benchmark_detail("x", db_path)
        assert result is None


class TestGetComparisonData:
    def test_returns_chart_data(self, benchmark_db: Path) -> None:
        db_path = benchmark_db / "benchmarks.db"
        benchmarks = get_all_benchmarks(db_path)
        bid = benchmarks[0]["id"]

        result = get_comparison_data(bid, db_path)
        assert result is not None
        assert set(result["fixtures"]) == {"small", "large"}
        assert set(result["implementations"]) == {"quicksort", "mergesort"}
        assert "quicksort" in result["time_data"]
        assert "mergesort" in result["memory_data"]
        assert "quicksort" in result["correctness_data"]
        assert "quicksort" in result["cpu_data"]
        assert result["cpu_count"] >= 1

    def test_nonexistent_benchmark(self, benchmark_db: Path) -> None:
        db_path = benchmark_db / "benchmarks.db"
        result = get_comparison_data("no-such-id", db_path)
        assert result is None

    def test_nonexistent_db(self, tmp_path: Path) -> None:
        result = get_comparison_data("x", tmp_path / "nope.db")
        assert result is None

    def test_exception_in_store(self, benchmark_db: Path) -> None:
        """Cover except block in get_comparison_data."""
        db_path = benchmark_db / "benchmarks.db"
        with patch(
            "lib.benchmarks.BenchmarkStore.get_benchmark",
            side_effect=RuntimeError("boom"),
        ):
            result = get_comparison_data("x", db_path)
        assert result is None


class TestDeleteBenchmark:
    def test_delete_existing(self, benchmark_db: Path) -> None:
        db_path = benchmark_db / "benchmarks.db"
        benchmarks = get_all_benchmarks(db_path)
        bid = benchmarks[0]["id"]

        result = delete_benchmark(bid, db_path)
        assert result["success"] is True

        # Verify it's gone
        assert get_benchmark_detail(bid, db_path) is None

    def test_nonexistent_db(self, tmp_path: Path) -> None:
        result = delete_benchmark("x", tmp_path / "nope.db")
        assert result["success"] is False
        assert "Database not found" in result["error"]

    def test_exception_in_delete(self, benchmark_db: Path) -> None:
        """Cover except block in delete_benchmark."""
        db_path = benchmark_db / "benchmarks.db"
        with patch(
            "lib.benchmarks.BenchmarkStore.delete_benchmark",
            side_effect=RuntimeError("fail"),
        ):
            result = delete_benchmark("x", db_path)
        assert result["success"] is False
        assert "fail" in result["error"]
