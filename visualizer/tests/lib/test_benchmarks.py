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
from lib.exceptions import BenchmarkNotFoundError, DatabaseNotFoundError


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

        with pytest.raises(DatabaseNotFoundError):
            _get_store(tmp_path / "nope.db")

    def test_existing_path(self, benchmark_db: Path) -> None:
        store = _get_store(benchmark_db / "benchmarks.db")
        assert store is not None
        store.close()

    def test_directory_path(self, tmp_path: Path) -> None:
        """A directory is not a valid database file."""

        with pytest.raises(DatabaseNotFoundError):
            _get_store(tmp_path)


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

        with pytest.raises(BenchmarkNotFoundError):
            get_benchmark_detail("no-such-id", db_path)

    def test_nonexistent_db(self, tmp_path: Path) -> None:

        with pytest.raises(DatabaseNotFoundError):
            get_benchmark_detail("x", tmp_path / "nope.db")

    def test_exception_in_store(self, benchmark_db: Path) -> None:
        """Cover except block — exception propagates now."""
        db_path = benchmark_db / "benchmarks.db"

        with patch(
            "lib.benchmarks.BenchmarkStore.get_benchmark",
            side_effect=RuntimeError("boom"),
        ):

            with pytest.raises(RuntimeError):
                get_benchmark_detail("x", db_path)


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

        with pytest.raises(BenchmarkNotFoundError):
            get_comparison_data("no-such-id", db_path)

    def test_nonexistent_db(self, tmp_path: Path) -> None:

        with pytest.raises(DatabaseNotFoundError):
            get_comparison_data("x", tmp_path / "nope.db")

    def test_exception_in_store(self, benchmark_db: Path) -> None:
        """Cover except block — exception propagates now."""
        db_path = benchmark_db / "benchmarks.db"

        with patch(
            "lib.benchmarks.BenchmarkStore.get_benchmark",
            side_effect=RuntimeError("boom"),
        ):

            with pytest.raises(RuntimeError):
                get_comparison_data("x", db_path)


class TestDeleteBenchmark:
    def test_delete_existing(self, benchmark_db: Path) -> None:
        db_path = benchmark_db / "benchmarks.db"
        benchmarks = get_all_benchmarks(db_path)
        bid = benchmarks[0]["id"]

        delete_benchmark(bid, db_path)

        with pytest.raises(BenchmarkNotFoundError):
            get_benchmark_detail(bid, db_path)

    def test_nonexistent_db(self, tmp_path: Path) -> None:

        with pytest.raises(DatabaseNotFoundError):
            delete_benchmark("x", tmp_path / "nope.db")

    def test_exception_in_delete(self, benchmark_db: Path) -> None:
        """Cover except block — exception propagates now."""
        db_path = benchmark_db / "benchmarks.db"

        with patch(
            "lib.benchmarks.BenchmarkStore.delete_benchmark",
            side_effect=RuntimeError("fail"),
        ):

            with pytest.raises(RuntimeError):
                delete_benchmark("x", db_path)
