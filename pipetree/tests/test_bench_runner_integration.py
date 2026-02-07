"""Tests for BenchRunner integration with BenchmarkStore."""

import tempfile
from pathlib import Path

import pytest

from pipetree import Capability, Pipetree, Registry, Step
from pipetree.benchmark import BenchResult, BenchRunner, Fixture, Metrics
from pipetree.infrastructure.progress.benchmark_store import BenchmarkStore
from pipetree.types import Context
from tests.fixtures import MockContext


class TestBenchRunnerWithStore:
    """Tests for BenchRunner with BenchmarkStore integration."""

    @pytest.fixture
    def store_and_registry(self) -> tuple[BenchmarkStore, Registry]:
        """Create a store and registry for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "benchmarks.db"
            store = BenchmarkStore(db_path)

            registry = Registry()
            cap = Capability(name="test", requires=set(), provides={"value"})

            class FastStep(Step):
                def run(self, ctx: Context) -> Context:
                    ctx.value = 10  # type: ignore
                    return ctx

            registry.register("test", "fast", lambda: FastStep(cap, "fast"))
            yield store, registry
            store.close()

    def test_run_step_ab_with_store(
        self, store_and_registry: tuple[BenchmarkStore, Registry]
    ) -> None:
        """Test that run_step_ab persists results to store."""
        store, registry = store_and_registry

        runner = BenchRunner(registry=registry, track_memory=False, store=store)

        fixtures: list[Fixture] = [
            {"id": "fixture1", "path": "/test1", "expected": {"value": 10}},
        ]

        def judge(fixture: Fixture, ctx: Context) -> Metrics:
            return {"correctness": 1.0}

        def setup_ctx(fixture: Fixture) -> MockContext:
            return MockContext(path=fixture.get("path", ""))

        results = runner.run_step_ab(
            cap_name="test",
            impls=["fast"],
            fixtures=fixtures,
            judge=judge,
            setup_ctx=setup_ctx,
            name="Test Benchmark",
            description="Test description",
        )

        assert len(results) == 1

        # Check that benchmark was stored
        benchmarks = store.get_all_benchmarks()
        assert len(benchmarks) == 1
        assert benchmarks[0]["name"] == "Test Benchmark"
        assert benchmarks[0]["status"] == "completed"

    def test_run_step_ab_with_store_on_error(self) -> None:
        """Test that store marks benchmark as failed when step raises."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "benchmarks.db"
            store = BenchmarkStore(db_path)

            registry = Registry()
            cap = Capability(name="error", requires=set(), provides={"x"})

            class ErrorStep(Step):
                def run(self, ctx: Context) -> Context:
                    raise RuntimeError("Benchmark failed!")

            registry.register("error", "failing", lambda: ErrorStep(cap, "error"))

            runner = BenchRunner(registry=registry, track_memory=False, store=store)
            fixtures: list[Fixture] = [{"id": "test", "path": "/test"}]

            def setup_ctx(fixture: Fixture) -> MockContext:
                return MockContext(path=fixture.get("path", ""))

            # The runner catches step errors and returns them in results
            results = runner.run_step_ab(
                cap_name="error",
                impls=["failing"],
                fixtures=fixtures,
                judge=lambda f, c: {},
                setup_ctx=setup_ctx,
            )

            assert len(results) == 1
            assert results[0].error is not None

            # Check benchmark was marked completed (not failed, since the error was caught)
            benchmarks = store.get_all_benchmarks()
            assert len(benchmarks) == 1
            assert benchmarks[0]["status"] == "completed"

            store.close()

    def test_run_step_ab_with_extra_metrics(self) -> None:
        """Test that extra metrics are persisted to store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "benchmarks.db"
            store = BenchmarkStore(db_path)

            registry = Registry()
            cap = Capability(name="test", requires=set(), provides={"value"})

            class TestStep(Step):
                def run(self, ctx: Context) -> Context:
                    ctx.value = 10  # type: ignore
                    return ctx

            registry.register("test", "impl", lambda: TestStep(cap, "impl"))

            runner = BenchRunner(registry=registry, track_memory=False, store=store)
            fixtures: list[Fixture] = [{"id": "fixture1"}]

            def judge(fixture: Fixture, ctx: Context) -> Metrics:
                return {
                    "correctness": 1.0,
                    "custom_metric": 42.0,
                    "another_metric": "value",
                }

            def setup_ctx(fixture: Fixture) -> MockContext:
                return MockContext()

            runner.run_step_ab(
                cap_name="test",
                impls=["impl"],
                fixtures=fixtures,
                judge=judge,
                setup_ctx=setup_ctx,
            )

            # Check that results were stored with extra metrics
            benchmarks = store.get_all_benchmarks()
            results = store.get_results(benchmarks[0]["id"])
            assert len(results) == 1
            assert results[0]["correctness"] == 1.0
            # Extra metrics should be in extra_metrics JSON
            assert results[0]["extra_metrics"] is not None

            store.close()


class TestBenchRunnerMemoryTracking:
    """Tests for BenchRunner with memory tracking enabled."""

    def test_run_step_with_memory_tracking(self) -> None:
        """Test that memory tracking captures peak memory."""
        registry = Registry()
        cap = Capability(name="test", requires=set(), provides={"value"})

        class MemoryStep(Step):
            def run(self, ctx: Context) -> Context:
                # Allocate some memory
                _ = [0] * 10000
                ctx.value = 10  # type: ignore
                return ctx

        registry.register("test", "mem", lambda: MemoryStep(cap, "mem"))

        runner = BenchRunner(registry=registry, track_memory=True)
        fixtures: list[Fixture] = [{"id": "test"}]

        def setup_ctx(fixture: Fixture) -> MockContext:
            return MockContext()

        results = runner.run_step_ab(
            cap_name="test",
            impls=["mem"],
            fixtures=fixtures,
            judge=lambda f, c: {},
            setup_ctx=setup_ctx,
        )

        assert len(results) == 1
        assert "peak_mem_mb" in results[0].metrics
        assert results[0].metrics["peak_mem_mb"] >= 0

    def test_run_pipeline_with_memory_tracking(self) -> None:
        """Test pipeline benchmarking with memory tracking."""
        cap = Capability(name="test", requires=set(), provides={"result"})

        class TestStep(Step):
            def run(self, ctx: Context) -> Context:
                _ = [0] * 10000
                ctx.result = "done"  # type: ignore
                return ctx

        pipeline = Pipetree(steps=[TestStep(cap, "test")])
        runner = BenchRunner(registry=Registry(), track_memory=True)
        fixtures: list[Fixture] = [{"id": "test"}]

        def setup_ctx(fixture: Fixture) -> MockContext:
            return MockContext()

        results = runner.run_pipeline_ab(
            candidates={"pipeline": pipeline},
            fixtures=fixtures,
            judge=lambda f, c: {},
            setup_ctx=setup_ctx,
        )

        assert len(results) == 1
        assert "peak_mem_mb" in results[0].metrics

    def test_run_step_memory_tracking_on_error(self) -> None:
        """Test that memory tracking is stopped on error."""
        registry = Registry()
        cap = Capability(name="error", requires=set(), provides={"x"})

        class ErrorStep(Step):
            def run(self, ctx: Context) -> Context:
                raise RuntimeError("Error!")

        registry.register("error", "err", lambda: ErrorStep(cap, "err"))

        runner = BenchRunner(registry=registry, track_memory=True)
        fixtures: list[Fixture] = [{"id": "test"}]

        def setup_ctx(fixture: Fixture) -> MockContext:
            return MockContext()

        results = runner.run_step_ab(
            cap_name="error",
            impls=["err"],
            fixtures=fixtures,
            judge=lambda f, c: {},
            setup_ctx=setup_ctx,
        )

        assert len(results) == 1
        assert results[0].error is not None


class TestBenchRunnerAsyncSteps:
    """Tests for BenchRunner with async steps."""

    def test_run_step_ab_with_async_step(self) -> None:
        """Test that async steps are properly handled."""
        registry = Registry()
        cap = Capability(name="async_test", requires=set(), provides={"value"})

        class AsyncStep(Step):
            async def run(self, ctx: Context) -> Context:
                import asyncio

                await asyncio.sleep(0.01)
                ctx.value = 42  # type: ignore
                return ctx

        registry.register("async_test", "async", lambda: AsyncStep(cap, "async"))

        runner = BenchRunner(registry=registry, track_memory=False)
        fixtures: list[Fixture] = [{"id": "test"}]

        def setup_ctx(fixture: Fixture) -> MockContext:
            return MockContext()

        results = runner.run_step_ab(
            cap_name="async_test",
            impls=["async"],
            fixtures=fixtures,
            judge=lambda f, c: {"correctness": 1.0 if c.value == 42 else 0.0},
            setup_ctx=setup_ctx,
        )

        assert len(results) == 1
        assert results[0].metrics["correctness"] == 1.0


class TestBenchRunnerPipelineErrors:
    """Tests for BenchRunner pipeline error handling."""

    def test_run_pipeline_with_error(self) -> None:
        """Test pipeline benchmarking handles errors."""
        cap = Capability(name="error", requires=set(), provides={"result"})

        class ErrorStep(Step):
            def run(self, ctx: Context) -> Context:
                raise RuntimeError("Pipeline failed!")

        pipeline = Pipetree(steps=[ErrorStep(cap, "error")])
        runner = BenchRunner(registry=Registry(), track_memory=True)
        fixtures: list[Fixture] = [{"id": "test"}]

        def setup_ctx(fixture: Fixture) -> MockContext:
            return MockContext()

        results = runner.run_pipeline_ab(
            candidates={"failing": pipeline},
            fixtures=fixtures,
            judge=lambda f, c: {},
            setup_ctx=setup_ctx,
        )

        assert len(results) == 1
        assert results[0].error is not None
        assert "Pipeline failed!" in results[0].error


class TestBenchmarkStoreEdgeCases:
    """Tests for BenchmarkStore edge cases."""

    def test_create_benchmark_after_close(self) -> None:
        """Test that create_benchmark raises when connection is closed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            store = BenchmarkStore(db_path)
            store.close()

            with pytest.raises(RuntimeError, match="Database not initialized"):
                store.create_benchmark("test", "cap")

    def test_add_result_after_close(self) -> None:
        """Test that add_result raises when connection is closed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            store = BenchmarkStore(db_path)
            store.close()

            with pytest.raises(RuntimeError, match="Database not initialized"):
                store.add_result("bench_id", "impl", "fixture")

    def test_methods_return_defaults_after_close(self) -> None:
        """Test that query methods return empty results after close."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            store = BenchmarkStore(db_path)
            benchmark_id = store.create_benchmark("test", "cap")
            store.close()

            # These should return empty/None instead of raising
            assert store.get_benchmark(benchmark_id) is None
            assert store.get_results(benchmark_id) == []
            assert store.get_all_benchmarks() == []
            assert store.get_implementations(benchmark_id) == []
            assert store.get_summary(benchmark_id) == {}
            assert store.delete_benchmark(benchmark_id) is False

            # complete_benchmark should not raise
            store.complete_benchmark(benchmark_id)

    def test_delete_benchmark_exception_handling(self) -> None:
        """Test that delete_benchmark handles exceptions gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            store = BenchmarkStore(db_path)

            # Try to delete non-existent benchmark (should return False)
            result = store.delete_benchmark("non_existent")
            assert result is False

            store.close()

    def test_delete_benchmark_returns_false_on_exception(self) -> None:
        """Test that delete_benchmark returns False when an exception occurs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            store = BenchmarkStore(db_path)

            # Create a valid benchmark
            benchmark_id = store.create_benchmark("test", "cap")

            # Close the connection to trigger an exception in delete
            original_conn = store._conn
            store._conn = None

            # Should return False when conn is None
            result = store.delete_benchmark(benchmark_id)
            assert result is False

            # Restore and close properly
            store._conn = original_conn
            store.close()


class TestBenchRunnerStoreException:
    """Test BenchRunner exception handling with store."""

    def test_run_step_ab_marks_benchmark_failed_on_registry_error(self) -> None:
        """Test benchmark is marked failed when registry raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "benchmarks.db"
            store = BenchmarkStore(db_path)

            # Create an empty registry - make will fail
            registry = Registry()

            runner = BenchRunner(registry=registry, track_memory=False, store=store)
            fixtures: list[Fixture] = [{"id": "test"}]

            def setup_ctx(fixture: Fixture) -> MockContext:
                return MockContext()

            # This should raise because "nonexistent" cap doesn't exist
            with pytest.raises(KeyError):
                runner.run_step_ab(
                    cap_name="nonexistent",
                    impls=["impl"],
                    fixtures=fixtures,
                    judge=lambda f, c: {},
                    setup_ctx=setup_ctx,
                )

            # Check benchmark was marked as failed
            benchmarks = store.get_all_benchmarks()
            assert len(benchmarks) == 1
            assert benchmarks[0]["status"] == "failed"

            store.close()

    def test_persist_result_without_store(self) -> None:
        """Test _persist_result returns early when no store configured."""
        registry = Registry()
        runner = BenchRunner(registry=registry, track_memory=False, store=None)

        # Should not raise - just returns early
        result = BenchResult(impl_name="test", fixture_id="test", metrics={})
        runner._persist_result("benchmark_id", result)
