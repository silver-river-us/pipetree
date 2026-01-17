"""Tests for the Pipeline class."""

import pytest

from ingestion.capability import Capability
from ingestion.pipeline import ContractViolationError, Pipeline
from ingestion.step import BaseStep
from ingestion.types import Ctx


class TestPipeline:
    def test_pipeline_creation(self) -> None:
        cap = Capability(name="test", requires=set(), provides={"a"})

        class TestStep(BaseStep):
            def run(self, ctx: Ctx) -> Ctx:
                ctx["a"] = 1
                return ctx

        step = TestStep(cap=cap, name="step1")
        pipeline = Pipeline(steps=[step])
        assert len(pipeline.steps) == 1

    @pytest.mark.asyncio
    async def test_pipeline_runs_steps_in_order(self) -> None:
        cap1 = Capability(name="step1", requires=set(), provides={"a"})
        cap2 = Capability(name="step2", requires={"a"}, provides={"b"})

        class Step1(BaseStep):
            def run(self, ctx: Ctx) -> Ctx:
                ctx["a"] = 1
                ctx["order"] = [1]
                return ctx

        class Step2(BaseStep):
            def run(self, ctx: Ctx) -> Ctx:
                ctx["b"] = ctx["a"] + 1  # type: ignore
                ctx["order"].append(2)  # type: ignore
                return ctx

        pipeline = Pipeline(
            steps=[
                Step1(cap=cap1, name="step1"),
                Step2(cap=cap2, name="step2"),
            ]
        )

        result = await pipeline.run("/test/path")
        assert result["a"] == 1
        assert result["b"] == 2
        assert result["order"] == [1, 2]  # type: ignore

    @pytest.mark.asyncio
    async def test_pipeline_validates_preconditions(self) -> None:
        cap = Capability(name="test", requires={"missing_key"}, provides={"a"})

        class TestStep(BaseStep):
            def run(self, ctx: Ctx) -> Ctx:
                ctx["a"] = 1
                return ctx

        pipeline = Pipeline(steps=[TestStep(cap=cap, name="step1")])

        with pytest.raises(ContractViolationError, match="requires"):
            await pipeline.run("/test/path")

    @pytest.mark.asyncio
    async def test_pipeline_validates_postconditions(self) -> None:
        cap = Capability(name="test", requires=set(), provides={"promised_key"})

        class BadStep(BaseStep):
            def run(self, ctx: Ctx) -> Ctx:
                # Does not provide "promised_key"
                return ctx

        pipeline = Pipeline(steps=[BadStep(cap=cap, name="bad_step")])

        with pytest.raises(ContractViolationError, match="must provide"):
            await pipeline.run("/test/path")

    @pytest.mark.asyncio
    async def test_pipeline_supports_async_steps(self) -> None:
        cap = Capability(name="async_test", requires=set(), provides={"result"})

        class AsyncStep(BaseStep):
            async def run(self, ctx: Ctx) -> Ctx:
                ctx["result"] = "async_done"
                return ctx

        pipeline = Pipeline(steps=[AsyncStep(cap=cap, name="async_step")])
        result = await pipeline.run("/test/path")
        assert result["result"] == "async_done"

    @pytest.mark.asyncio
    async def test_pipeline_mixed_sync_async(self) -> None:
        cap1 = Capability(name="sync", requires=set(), provides={"a"})
        cap2 = Capability(name="async", requires={"a"}, provides={"b"})

        class SyncStep(BaseStep):
            def run(self, ctx: Ctx) -> Ctx:
                ctx["a"] = "sync"
                return ctx

        class AsyncStep(BaseStep):
            async def run(self, ctx: Ctx) -> Ctx:
                ctx["b"] = "async"
                return ctx

        pipeline = Pipeline(
            steps=[
                SyncStep(cap=cap1, name="sync"),
                AsyncStep(cap=cap2, name="async"),
            ]
        )

        result = await pipeline.run("/test/path")
        assert result["a"] == "sync"
        assert result["b"] == "async"

    def test_pipeline_repr(self) -> None:
        cap = Capability(name="test", requires=set(), provides=set())

        class TestStep(BaseStep):
            def run(self, ctx: Ctx) -> Ctx:
                return ctx

        pipeline = Pipeline(
            steps=[
                TestStep(cap=cap, name="step1"),
                TestStep(cap=cap, name="step2"),
            ]
        )

        repr_str = repr(pipeline)
        assert "step1" in repr_str
        assert "step2" in repr_str
