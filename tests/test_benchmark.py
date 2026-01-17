"""Tests for the benchmarking framework."""

import pytest

from ingestion.benchmark import (
    BenchResult,
    BenchRunner,
    Fixture,
    Metrics,
    accuracy_judge,
)
from ingestion.capability import Capability
from ingestion.pipeline import Pipeline
from ingestion.registry import Registry
from ingestion.step import BaseStep
from ingestion.types import Ctx


class TestBenchRunner:
    @pytest.fixture
    def registry_with_impls(self) -> Registry:
        registry = Registry()
        cap = Capability(name="test", requires=set(), provides={"value"})

        class FastStep(BaseStep):
            def run(self, ctx: Ctx) -> Ctx:
                ctx["value"] = 10
                return ctx

        class SlowStep(BaseStep):
            def run(self, ctx: Ctx) -> Ctx:
                ctx["value"] = 20
                return ctx

        registry.register("test", "fast", lambda: FastStep(cap, "fast"))
        registry.register("test", "slow", lambda: SlowStep(cap, "slow"))

        return registry

    @pytest.mark.asyncio
    async def test_run_step_ab(self, registry_with_impls: Registry) -> None:
        runner = BenchRunner(registry=registry_with_impls, track_memory=False)

        fixtures: list[Fixture] = [
            {"id": "fixture1", "path": "/test1", "expected": {"value": 10}},
        ]

        def judge(fixture: Fixture, ctx: Ctx) -> Metrics:
            expected = fixture.get("expected", {}).get("value")
            actual = ctx.get("value")
            return {"correctness": 1.0 if expected == actual else 0.0}

        results = await runner.run_step_ab(
            cap_name="test",
            impls=["fast", "slow"],
            fixtures=fixtures,
            judge=judge,
        )

        assert len(results) == 2

        fast_result = next(r for r in results if r.impl_name == "fast")
        slow_result = next(r for r in results if r.impl_name == "slow")

        assert fast_result.metrics["correctness"] == 1.0
        assert slow_result.metrics["correctness"] == 0.0

    @pytest.mark.asyncio
    async def test_run_pipeline_ab(self) -> None:
        cap = Capability(name="test", requires=set(), provides={"result"})

        class StepA(BaseStep):
            def run(self, ctx: Ctx) -> Ctx:
                ctx["result"] = "A"
                return ctx

        class StepB(BaseStep):
            def run(self, ctx: Ctx) -> Ctx:
                ctx["result"] = "B"
                return ctx

        pipeline_a = Pipeline(steps=[StepA(cap, "step_a")])
        pipeline_b = Pipeline(steps=[StepB(cap, "step_b")])

        runner = BenchRunner(registry=Registry(), track_memory=False)

        fixtures: list[Fixture] = [
            {"id": "test", "path": "/test", "expected": {"result": "A"}},
        ]

        def judge(fixture: Fixture, ctx: Ctx) -> Metrics:
            expected = fixture.get("expected", {}).get("result")
            actual = ctx.get("result")
            return {"correctness": 1.0 if expected == actual else 0.0}

        results = await runner.run_pipeline_ab(
            candidates={"pipeline_a": pipeline_a, "pipeline_b": pipeline_b},
            fixtures=fixtures,
            judge=judge,
        )

        assert len(results) == 2

        result_a = next(r for r in results if r.impl_name == "pipeline_a")
        result_b = next(r for r in results if r.impl_name == "pipeline_b")

        assert result_a.metrics["correctness"] == 1.0
        assert result_b.metrics["correctness"] == 0.0

    @pytest.mark.asyncio
    async def test_captures_wall_time(self, registry_with_impls: Registry) -> None:
        runner = BenchRunner(registry=registry_with_impls, track_memory=False)

        fixtures: list[Fixture] = [{"id": "test", "path": "/test"}]

        def judge(fixture: Fixture, ctx: Ctx) -> Metrics:
            return {}

        results = await runner.run_step_ab(
            cap_name="test",
            impls=["fast"],
            fixtures=fixtures,
            judge=judge,
        )

        assert len(results) == 1
        assert "wall_time_s" in results[0].metrics
        assert results[0].metrics["wall_time_s"] >= 0

    @pytest.mark.asyncio
    async def test_handles_step_errors(self, registry_with_impls: Registry) -> None:
        registry = Registry()
        cap = Capability(name="error", requires=set(), provides={"x"})

        class ErrorStep(BaseStep):
            def run(self, ctx: Ctx) -> Ctx:
                raise RuntimeError("Step failed!")

        registry.register("error", "failing", lambda: ErrorStep(cap, "error"))

        runner = BenchRunner(registry=registry, track_memory=False)
        fixtures: list[Fixture] = [{"id": "test", "path": "/test"}]

        results = await runner.run_step_ab(
            cap_name="error",
            impls=["failing"],
            fixtures=fixtures,
            judge=lambda f, c: {},
        )

        assert len(results) == 1
        assert results[0].error is not None
        assert "Step failed!" in results[0].error


class TestAccuracyJudge:
    def test_all_correct(self) -> None:
        fixture: Fixture = {
            "id": "test",
            "expected": {"kind": "ops", "scanned": True},
        }
        ctx: Ctx = {"kind": "ops", "scanned": True}

        metrics = accuracy_judge(fixture, ctx)
        assert metrics["correctness"] == 1.0

    def test_all_wrong(self) -> None:
        fixture: Fixture = {
            "id": "test",
            "expected": {"kind": "ops", "scanned": True},
        }
        ctx: Ctx = {"kind": "parts", "scanned": False}

        metrics = accuracy_judge(fixture, ctx)
        assert metrics["correctness"] == 0.0

    def test_partial_match(self) -> None:
        fixture: Fixture = {
            "id": "test",
            "expected": {"kind": "ops", "scanned": True},
        }
        ctx: Ctx = {"kind": "ops", "scanned": False}

        metrics = accuracy_judge(fixture, ctx)
        assert metrics["correctness"] == 0.5

    def test_empty_expected(self) -> None:
        fixture: Fixture = {"id": "test", "expected": {}}
        ctx: Ctx = {"kind": "ops"}

        metrics = accuracy_judge(fixture, ctx)
        assert metrics["correctness"] == 0.0


class TestBenchResult:
    def test_bench_result_creation(self) -> None:
        result = BenchResult(
            impl_name="impl1",
            fixture_id="fixture1",
            metrics={"correctness": 0.95, "wall_time_s": 1.5},
        )

        assert result.impl_name == "impl1"
        assert result.fixture_id == "fixture1"
        assert result.metrics["correctness"] == 0.95
        assert result.error is None

    def test_bench_result_with_error(self) -> None:
        result = BenchResult(
            impl_name="impl1",
            fixture_id="fixture1",
            metrics={},
            error="Something went wrong",
        )

        assert result.error == "Something went wrong"
