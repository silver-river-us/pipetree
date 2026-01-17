"""Benchmark runner for A/B testing."""

import asyncio
import time
import tracemalloc
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from ingestion.benchmarking.bench_result import BenchResult
from ingestion.benchmarking.fixture import Fixture
from ingestion.benchmarking.judges import JudgeFn
from ingestion.domain.pipeline.pipeline import Pipeline
from ingestion.domain.step.step_protocol import Step
from ingestion.domain.types.context import Ctx
from ingestion.infrastructure.registry.registry import Registry


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
        setup_ctx: Callable[[Fixture], Ctx] | None = None,
    ) -> list[BenchResult]:
        """
        Benchmark multiple implementations of a capability.

        Args:
            cap_name: Capability name to benchmark
            impls: List of implementation names to compare
            fixtures: Test fixtures
            judge: Function to evaluate correctness
            setup_ctx: Optional function to set up initial context

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
        candidates: Mapping[str, Pipeline],
        fixtures: list[Fixture],
        judge: JudgeFn,
    ) -> list[BenchResult]:
        """
        Benchmark multiple pipeline configurations.

        Args:
            candidates: Map of pipeline names to pipelines
            fixtures: Test fixtures
            judge: Function to evaluate correctness

        Returns:
            List of benchmark results
        """
        results: list[BenchResult] = []

        for name, pipeline in candidates.items():
            for fixture in fixtures:
                result = await self._run_pipeline(pipeline, fixture, judge)
                result.impl_name = name
                results.append(result)

        return results

    async def _run_single(
        self,
        step: Step,
        fixture: Fixture,
        judge: JudgeFn,
        setup_ctx: Callable[[Fixture], Ctx] | None = None,
    ) -> BenchResult:
        """Run a single step benchmark."""
        fixture_id = fixture.get("id", fixture.get("path", "unknown"))

        # Set up context
        ctx: Ctx
        if setup_ctx:
            ctx = setup_ctx(fixture)
        else:
            ctx = {"path": fixture.get("path", "")}

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
        pipeline: Pipeline,
        fixture: Fixture,
        judge: JudgeFn,
    ) -> BenchResult:
        """Run a full pipeline benchmark."""
        fixture_id = fixture.get("id", fixture.get("path", "unknown"))
        path = fixture.get("path", "")

        if self.track_memory:
            tracemalloc.start()

        start_time = time.perf_counter()

        try:
            ctx = await pipeline.run(path)
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
