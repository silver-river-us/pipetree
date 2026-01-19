"""Benchmark runner for A/B testing."""

from __future__ import annotations

import asyncio
import contextlib
import time
import tracemalloc
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pipetree.benchmarking.bench_result import BenchResult
from pipetree.benchmarking.fixture import Fixture
from pipetree.benchmarking.judges import JudgeFn
from pipetree.domain.pipeline.pipeline import Pipetree
from pipetree.domain.step.step import Step
from pipetree.domain.types.context import Context
from pipetree.infrastructure.registry.registry import Registry

if TYPE_CHECKING:
    from pipetree.infrastructure.progress.benchmark_store import BenchmarkStore


@dataclass
class BenchRunner:
    """
    Runner for benchmarking steps and pipelines.

    Supports:
    - A/B/C testing of step implementations
    - Full pipeline comparison
    - Correctness evaluation via judge functions
    - Performance metrics collection
    - Optional persistence to BenchmarkStore
    """

    registry: Registry
    track_memory: bool = True
    store: BenchmarkStore | None = field(default=None)

    def run_step_ab(
        self,
        cap_name: str,
        impls: list[str],
        fixtures: list[Fixture],
        judge: JudgeFn,
        setup_ctx: Callable[[Fixture], Context],
        name: str | None = None,
        description: str | None = None,
    ) -> list[BenchResult]:
        """
        Benchmark multiple implementations of a capability.

        Args:
            cap_name: Capability name to benchmark
            impls: List of implementation names to compare
            fixtures: Test fixtures
            judge: Function to evaluate correctness
            setup_ctx: Function to create initial context from fixture
            name: Optional benchmark name (for persistence)
            description: Optional benchmark description (for persistence)

        Returns:
            List of benchmark results
        """
        results: list[BenchResult] = []
        benchmark_id: str | None = None

        # Create benchmark record if store is configured
        if self.store:
            benchmark_name = name or f"{cap_name} comparison"
            benchmark_id = self.store.create_benchmark(
                name=benchmark_name,
                capability=cap_name,
                description=description,
            )

        try:
            total_runs = len(impls) * len(fixtures)
            current_run = 0

            for impl_name in impls:
                print(f"\n[benchmark] Loading implementation: {impl_name}")
                step = self.registry.make(cap_name, impl_name)

                for fixture in fixtures:
                    current_run += 1
                    fixture_id = fixture.get("id", fixture.get("path", "unknown"))
                    print(
                        f"[benchmark] ({current_run}/{total_runs}) Running {impl_name} on {fixture_id}..."
                    )

                    result = self._run_single(step, fixture, judge, setup_ctx)
                    result.impl_name = impl_name
                    results.append(result)

                    # Log result
                    if result.error:
                        print(f"[benchmark]   ERROR: {result.error}")
                    else:
                        m = result.metrics
                        print(
                            f"[benchmark]   Wall: {m.get('wall_time_s', 0):.3f}s | "
                            f"CPU: {m.get('cpu_time_s', 0):.3f}s | "
                            f"Mem: {m.get('peak_mem_mb', 0):.1f}MB | "
                            f"Correctness: {m.get('correctness', 0):.1%}"
                        )

                    # Persist result if store is configured
                    if self.store and benchmark_id:
                        self._persist_result(benchmark_id, result)

            # Mark benchmark as completed
            if self.store and benchmark_id:
                self.store.complete_benchmark(benchmark_id, "completed")

        except Exception:
            if self.store and benchmark_id:
                self.store.complete_benchmark(benchmark_id, "failed")
            raise

        return results

    def _persist_result(self, benchmark_id: str, result: BenchResult) -> None:
        """Persist a benchmark result to the store."""
        if not self.store:
            return

        metrics = result.metrics
        extra = {
            k: v
            for k, v in metrics.items()
            if k
            not in {
                "wall_time_s",
                "peak_mem_mb",
                "correctness",
                "throughput_items_s",
                "items_processed",
                "cpu_time_s",
            }
        }

        self.store.add_result(
            benchmark_id=benchmark_id,
            impl_name=result.impl_name,
            fixture_id=result.fixture_id,
            wall_time_s=metrics.get("wall_time_s"),
            cpu_time_s=metrics.get("cpu_time_s"),
            peak_mem_mb=metrics.get("peak_mem_mb"),
            throughput_items_s=metrics.get("throughput_items_s"),
            items_processed=metrics.get("items_processed"),
            correctness=metrics.get("correctness"),
            extra_metrics=extra if extra else None,
            error=result.error,
        )

    def run_pipeline_ab(
        self,
        candidates: Mapping[str, Pipetree],
        fixtures: list[Fixture],
        judge: JudgeFn,
        setup_ctx: Callable[[Fixture], Context],
    ) -> list[BenchResult]:
        """
        Benchmark multiple pipeline configurations.

        Args:
            candidates: Map of pipeline names to pipelines
            fixtures: Test fixtures
            judge: Function to evaluate correctness
            setup_ctx: Function to create initial context from fixture

        Returns:
            List of benchmark results
        """
        results: list[BenchResult] = []

        for name, pipeline in candidates.items():
            for fixture in fixtures:
                result = self._run_pipeline(pipeline, fixture, judge, setup_ctx)
                result.impl_name = name
                results.append(result)

        return results

    def _run_single(
        self,
        step: Step,
        fixture: Fixture,
        judge: JudgeFn,
        setup_ctx: Callable[[Fixture], Context],
    ) -> BenchResult:
        """Run a single step benchmark."""
        fixture_id = fixture.get("id", fixture.get("path", "unknown"))

        # Set up context
        ctx = setup_ctx(fixture)

        # Track memory if enabled
        if self.track_memory:
            tracemalloc.start()

        start_time = time.perf_counter()
        start_cpu = time.process_time()

        try:
            # Run the step
            result = step.run(ctx)
            # Handle coroutines by running in a new event loop
            if asyncio.iscoroutine(result):
                ctx = asyncio.run(result)
            else:
                ctx = result  # type: ignore

            wall_time = time.perf_counter() - start_time
            cpu_time = time.process_time() - start_cpu

            # Get memory stats
            peak_mem_mb = 0.0
            if self.track_memory:
                _, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                peak_mem_mb = peak / (1024 * 1024)

            # Evaluate correctness
            metrics = judge(fixture, ctx)
            metrics["wall_time_s"] = wall_time
            metrics["cpu_time_s"] = cpu_time
            metrics["peak_mem_mb"] = peak_mem_mb

            return BenchResult(
                impl_name="",  # Set by caller
                fixture_id=fixture_id,
                metrics=metrics,
            )

        except Exception as e:
            if self.track_memory:
                with contextlib.suppress(Exception):
                    tracemalloc.stop()
            return BenchResult(
                impl_name="",
                fixture_id=fixture_id,
                metrics={},
                error=str(e),
            )

    def _run_pipeline(
        self,
        pipeline: Pipetree,
        fixture: Fixture,
        judge: JudgeFn,
        setup_ctx: Callable[[Fixture], Context],
    ) -> BenchResult:
        """Run a full pipeline benchmark."""
        fixture_id = fixture.get("id", fixture.get("path", "unknown"))

        # Set up context
        ctx = setup_ctx(fixture)

        if self.track_memory:
            tracemalloc.start()

        start_time = time.perf_counter()
        start_cpu = time.process_time()

        try:
            ctx = asyncio.run(pipeline.run(ctx))
            wall_time = time.perf_counter() - start_time
            cpu_time = time.process_time() - start_cpu

            peak_mem_mb = 0.0
            if self.track_memory:
                _, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                peak_mem_mb = peak / (1024 * 1024)

            metrics = judge(fixture, ctx)
            metrics["wall_time_s"] = wall_time
            metrics["cpu_time_s"] = cpu_time
            metrics["peak_mem_mb"] = peak_mem_mb

            return BenchResult(
                impl_name="",
                fixture_id=fixture_id,
                metrics=metrics,
            )

        except Exception as e:
            if self.track_memory:
                with contextlib.suppress(Exception):
                    tracemalloc.stop()
            return BenchResult(
                impl_name="",
                fixture_id=fixture_id,
                metrics={},
                error=str(e),
            )
