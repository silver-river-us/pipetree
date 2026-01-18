"""Benchmark runner for A/B testing."""

import asyncio
import time
import tracemalloc
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from pipetree.benchmarking.bench_result import BenchResult
from pipetree.benchmarking.fixture import Fixture
from pipetree.benchmarking.judges import JudgeFn
from pipetree.domain.pipeline.pipeline import Pipetree
from pipetree.domain.step.step import Step
from pipetree.domain.types.context import Context
from pipetree.infrastructure.registry.registry import Registry


@dataclass
class BenchRunner:
    """
    Runner for benchmarking steps and pipelines.

    Supports:
    - A/B/C testing of step implementations
    - Full pipeline comparison
    - Correctness evaluation via judge functions
    - Performance metrics collection
    """

    registry: Registry
    track_memory: bool = True

    async def run_step_ab(
        self,
        cap_name: str,
        impls: list[str],
        fixtures: list[Fixture],
        judge: JudgeFn,
        setup_ctx: Callable[[Fixture], Context],
    ) -> list[BenchResult]:
        """
        Benchmark multiple implementations of a capability.

        Args:
            cap_name: Capability name to benchmark
            impls: List of implementation names to compare
            fixtures: Test fixtures
            judge: Function to evaluate correctness
            setup_ctx: Function to create initial context from fixture

        Returns:
            List of benchmark results
        """
        results: list[BenchResult] = []

        for impl_name in impls:
            step = self.registry.make(cap_name, impl_name)

            for fixture in fixtures:
                result = await self._run_single(step, fixture, judge, setup_ctx)
                result.impl_name = impl_name
                results.append(result)

        return results

    async def run_pipeline_ab(
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
                result = await self._run_pipeline(pipeline, fixture, judge, setup_ctx)
                result.impl_name = name
                results.append(result)

        return results

    async def _run_single(
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

        try:
            # Run the step
            result = step.run(ctx)
            if asyncio.iscoroutine(result):
                ctx = await result
            else:
                ctx = result  # type: ignore

            wall_time = time.perf_counter() - start_time

            # Get memory stats
            peak_mem_mb = 0.0
            if self.track_memory:
                _, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                peak_mem_mb = peak / (1024 * 1024)

            # Evaluate correctness
            metrics = judge(fixture, ctx)
            metrics["wall_time_s"] = wall_time
            metrics["peak_mem_mb"] = peak_mem_mb

            return BenchResult(
                impl_name="",  # Set by caller
                fixture_id=fixture_id,
                metrics=metrics,
            )

        except Exception as e:
            if self.track_memory:
                tracemalloc.stop()
            return BenchResult(
                impl_name="",
                fixture_id=fixture_id,
                metrics={},
                error=str(e),
            )

    async def _run_pipeline(
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

        try:
            ctx = await pipeline.run(ctx)
            wall_time = time.perf_counter() - start_time

            peak_mem_mb = 0.0
            if self.track_memory:
                _, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                peak_mem_mb = peak / (1024 * 1024)

            metrics = judge(fixture, ctx)
            metrics["wall_time_s"] = wall_time
            metrics["peak_mem_mb"] = peak_mem_mb

            return BenchResult(
                impl_name="",
                fixture_id=fixture_id,
                metrics=metrics,
            )

        except Exception as e:
            if self.track_memory:
                tracemalloc.stop()
            return BenchResult(
                impl_name="",
                fixture_id=fixture_id,
                metrics={},
                error=str(e),
            )
