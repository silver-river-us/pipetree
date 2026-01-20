"""Tests for BenchmarkStore."""

import tempfile
from pathlib import Path

from pipetree.infrastructure.progress import BenchmarkStore


class TestBenchmarkStore:
    """Test BenchmarkStore functionality."""

    def test_create_benchmark(self) -> None:
        """Test creating a new benchmark."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "bench.db"
            store = BenchmarkStore(db_path)

            benchmark_id = store.create_benchmark(
                name="Test Benchmark",
                capability="text_extraction",
                description="A test benchmark",
            )

            assert benchmark_id is not None

            # Verify we can retrieve it
            benchmark = store.get_benchmark(benchmark_id)
            assert benchmark is not None
            assert benchmark["name"] == "Test Benchmark"
            assert benchmark["capability"] == "text_extraction"
            assert benchmark["description"] == "A test benchmark"
            assert benchmark["status"] == "running"

            store.close()

    def test_create_benchmark_with_custom_id(self) -> None:
        """Test creating a benchmark with custom ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "bench.db"
            store = BenchmarkStore(db_path)

            benchmark_id = store.create_benchmark(
                name="Custom ID Benchmark",
                capability="test",
                benchmark_id="custom-123",
            )

            assert benchmark_id == "custom-123"

            benchmark = store.get_benchmark("custom-123")
            assert benchmark is not None
            assert benchmark["id"] == "custom-123"

            store.close()

    def test_add_result(self) -> None:
        """Test adding benchmark results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "bench.db"
            store = BenchmarkStore(db_path)

            benchmark_id = store.create_benchmark(
                name="Results Test",
                capability="test",
            )

            result_id = store.add_result(
                benchmark_id=benchmark_id,
                impl_name="impl_a",
                fixture_id="fixture_1",
                wall_time_s=1.5,
                cpu_time_s=1.2,
                peak_mem_mb=100.5,
                throughput_items_s=50.0,
                items_processed=100,
                correctness=0.95,
                extra_metrics={"custom_metric": 42},
            )

            assert result_id > 0

            # Verify results can be retrieved
            results = store.get_results(benchmark_id)
            assert len(results) == 1
            assert results[0]["impl_name"] == "impl_a"
            assert results[0]["wall_time_s"] == 1.5
            assert results[0]["extra_metrics"] == {"custom_metric": 42}

            store.close()

    def test_add_result_with_error(self) -> None:
        """Test adding a result with an error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "bench.db"
            store = BenchmarkStore(db_path)

            benchmark_id = store.create_benchmark(
                name="Error Test",
                capability="test",
            )

            result_id = store.add_result(
                benchmark_id=benchmark_id,
                impl_name="impl_fail",
                fixture_id="fixture_1",
                error="Something went wrong",
            )

            assert result_id > 0

            results = store.get_results(benchmark_id)
            assert len(results) == 1
            assert results[0]["error"] == "Something went wrong"

            store.close()

    def test_get_results_filtered_by_impl(self) -> None:
        """Test getting results filtered by implementation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "bench.db"
            store = BenchmarkStore(db_path)

            benchmark_id = store.create_benchmark(
                name="Filter Test",
                capability="test",
            )

            store.add_result(
                benchmark_id=benchmark_id,
                impl_name="impl_a",
                fixture_id="fixture_1",
                wall_time_s=1.0,
            )
            store.add_result(
                benchmark_id=benchmark_id,
                impl_name="impl_b",
                fixture_id="fixture_1",
                wall_time_s=2.0,
            )
            store.add_result(
                benchmark_id=benchmark_id,
                impl_name="impl_a",
                fixture_id="fixture_2",
                wall_time_s=1.5,
            )

            # Get all results
            all_results = store.get_results(benchmark_id)
            assert len(all_results) == 3

            # Get filtered results
            impl_a_results = store.get_results(benchmark_id, impl_name="impl_a")
            assert len(impl_a_results) == 2
            assert all(r["impl_name"] == "impl_a" for r in impl_a_results)

            store.close()

    def test_complete_benchmark(self) -> None:
        """Test marking a benchmark as completed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "bench.db"
            store = BenchmarkStore(db_path)

            benchmark_id = store.create_benchmark(
                name="Complete Test",
                capability="test",
            )

            # Initially running
            benchmark = store.get_benchmark(benchmark_id)
            assert benchmark["status"] == "running"

            # Mark as completed
            store.complete_benchmark(benchmark_id)

            benchmark = store.get_benchmark(benchmark_id)
            assert benchmark["status"] == "completed"
            assert benchmark["completed_at"] is not None

            store.close()

    def test_complete_benchmark_with_custom_status(self) -> None:
        """Test marking a benchmark with a custom status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "bench.db"
            store = BenchmarkStore(db_path)

            benchmark_id = store.create_benchmark(
                name="Custom Status Test",
                capability="test",
            )

            store.complete_benchmark(benchmark_id, status="failed")

            benchmark = store.get_benchmark(benchmark_id)
            assert benchmark["status"] == "failed"

            store.close()

    def test_get_all_benchmarks(self) -> None:
        """Test getting all benchmarks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "bench.db"
            store = BenchmarkStore(db_path)

            store.create_benchmark(name="Bench 1", capability="cap_a")
            store.create_benchmark(name="Bench 2", capability="cap_b")
            store.create_benchmark(name="Bench 3", capability="cap_a")

            all_benchmarks = store.get_all_benchmarks()
            assert len(all_benchmarks) == 3

            store.close()

    def test_get_all_benchmarks_filtered_by_capability(self) -> None:
        """Test getting benchmarks filtered by capability."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "bench.db"
            store = BenchmarkStore(db_path)

            store.create_benchmark(name="Bench 1", capability="cap_a")
            store.create_benchmark(name="Bench 2", capability="cap_b")
            store.create_benchmark(name="Bench 3", capability="cap_a")

            cap_a_benchmarks = store.get_all_benchmarks(capability="cap_a")
            assert len(cap_a_benchmarks) == 2
            assert all(b["capability"] == "cap_a" for b in cap_a_benchmarks)

            store.close()

    def test_get_implementations(self) -> None:
        """Test getting unique implementation names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "bench.db"
            store = BenchmarkStore(db_path)

            benchmark_id = store.create_benchmark(
                name="Impl Test",
                capability="test",
            )

            store.add_result(
                benchmark_id=benchmark_id,
                impl_name="impl_z",
                fixture_id="f1",
            )
            store.add_result(
                benchmark_id=benchmark_id,
                impl_name="impl_a",
                fixture_id="f1",
            )
            store.add_result(
                benchmark_id=benchmark_id,
                impl_name="impl_z",
                fixture_id="f2",
            )

            impls = store.get_implementations(benchmark_id)
            assert impls == ["impl_a", "impl_z"]  # Sorted alphabetically

            store.close()

    def test_get_summary(self) -> None:
        """Test getting summary statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "bench.db"
            store = BenchmarkStore(db_path)

            benchmark_id = store.create_benchmark(
                name="Summary Test",
                capability="test",
            )

            # Add results for impl_a
            store.add_result(
                benchmark_id=benchmark_id,
                impl_name="impl_a",
                fixture_id="f1",
                wall_time_s=1.0,
                correctness=0.9,
            )
            store.add_result(
                benchmark_id=benchmark_id,
                impl_name="impl_a",
                fixture_id="f2",
                wall_time_s=2.0,
                correctness=1.0,
            )

            # Add results for impl_b with an error
            store.add_result(
                benchmark_id=benchmark_id,
                impl_name="impl_b",
                fixture_id="f1",
                wall_time_s=0.5,
                error="Failed",
            )

            summary = store.get_summary(benchmark_id)

            assert "impl_a" in summary
            assert summary["impl_a"]["fixture_count"] == 2
            assert summary["impl_a"]["avg_wall_time_s"] == 1.5
            assert summary["impl_a"]["avg_correctness"] == 0.95
            assert summary["impl_a"]["error_count"] == 0

            assert "impl_b" in summary
            assert summary["impl_b"]["error_count"] == 1

            store.close()

    def test_delete_benchmark(self) -> None:
        """Test deleting a benchmark."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "bench.db"
            store = BenchmarkStore(db_path)

            benchmark_id = store.create_benchmark(
                name="Delete Test",
                capability="test",
            )

            store.add_result(
                benchmark_id=benchmark_id,
                impl_name="impl_a",
                fixture_id="f1",
            )

            # Verify exists
            assert store.get_benchmark(benchmark_id) is not None
            assert len(store.get_results(benchmark_id)) == 1

            # Delete
            result = store.delete_benchmark(benchmark_id)
            assert result is True

            # Verify deleted
            assert store.get_benchmark(benchmark_id) is None
            assert len(store.get_results(benchmark_id)) == 0

            store.close()

    def test_delete_nonexistent_benchmark(self) -> None:
        """Test deleting a nonexistent benchmark returns False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "bench.db"
            store = BenchmarkStore(db_path)

            result = store.delete_benchmark("nonexistent-id")
            assert result is False

            store.close()

    def test_get_benchmark_nonexistent(self) -> None:
        """Test getting a nonexistent benchmark returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "bench.db"
            store = BenchmarkStore(db_path)

            benchmark = store.get_benchmark("nonexistent-id")
            assert benchmark is None

            store.close()

    def test_close_and_reopen(self) -> None:
        """Test that data persists after close and reopen."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "bench.db"

            # Create and close
            store = BenchmarkStore(db_path)
            benchmark_id = store.create_benchmark(
                name="Persist Test",
                capability="test",
            )
            store.add_result(
                benchmark_id=benchmark_id,
                impl_name="impl_a",
                fixture_id="f1",
                wall_time_s=1.0,
            )
            store.close()

            # Reopen and verify
            store2 = BenchmarkStore(db_path)
            benchmark = store2.get_benchmark(benchmark_id)
            assert benchmark is not None
            assert benchmark["name"] == "Persist Test"

            results = store2.get_results(benchmark_id)
            assert len(results) == 1

            store2.close()

    def test_creates_parent_directory(self) -> None:
        """Test that parent directories are created if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "subdir" / "nested" / "bench.db"

            store = BenchmarkStore(db_path)
            assert db_path.exists()
            store.close()
