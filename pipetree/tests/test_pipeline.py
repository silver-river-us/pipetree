"""Tests for the Pipeline class."""

import pytest

from pipetree import Capability, ContractViolationError, Pipetree, Step
from pipetree.types import Context
from tests.fixtures import MockContext


class TestPipetree:
    def test_pipetree_creation(self) -> None:
        cap = Capability(name="test", requires=set(), provides={"a"})

        class TestStep(Step):
            def run(self, ctx: Context) -> Context:
                ctx.a = 1  # type: ignore
                return ctx

        step = TestStep(cap=cap, name="step1")
        pipetree = Pipetree(steps=[step])
        assert len(pipetree.steps) == 1

    @pytest.mark.asyncio
    async def test_pipetree_runs_steps_in_order(self) -> None:
        cap1 = Capability(name="step1", requires=set(), provides={"a"})
        cap2 = Capability(name="step2", requires={"a"}, provides={"b"})

        class Step1(Step):
            def run(self, ctx: Context) -> Context:
                ctx.a = 1  # type: ignore
                ctx.order = [1]  # type: ignore
                return ctx

        class Step2(Step):
            def run(self, ctx: Context) -> Context:
                ctx.b = ctx.a + 1  # type: ignore
                ctx.order.append(2)  # type: ignore
                return ctx

        pipetree = Pipetree(
            steps=[
                Step1(cap=cap1, name="step1"),
                Step2(cap=cap2, name="step2"),
            ]
        )

        ctx = MockContext(path="/test/path")
        result = await pipetree.run(ctx)
        assert result.a == 1
        assert result.b == 2
        assert result.order == [1, 2]

    @pytest.mark.asyncio
    async def test_pipetree_validates_preconditions(self) -> None:
        cap = Capability(name="test", requires={"missing_key"}, provides={"a"})

        class TestStep(Step):
            def run(self, ctx: Context) -> Context:
                ctx.a = 1  # type: ignore
                return ctx

        pipetree = Pipetree(steps=[TestStep(cap=cap, name="step1")])

        with pytest.raises(ContractViolationError, match="requires"):
            await pipetree.run(MockContext(path="/test/path"))

    @pytest.mark.asyncio
    async def test_pipetree_validates_postconditions(self) -> None:
        cap = Capability(name="test", requires=set(), provides={"promised_key"})

        class BadStep(Step):
            def run(self, ctx: Context) -> Context:
                # Does not provide "promised_key"
                return ctx

        pipetree = Pipetree(steps=[BadStep(cap=cap, name="bad_step")])

        with pytest.raises(ContractViolationError, match="must provide"):
            await pipetree.run(MockContext(path="/test/path"))

    @pytest.mark.asyncio
    async def test_pipetree_supports_async_steps(self) -> None:
        cap = Capability(name="async_test", requires=set(), provides={"result"})

        class AsyncStep(Step):
            async def run(self, ctx: Context) -> Context:
                ctx.result = "async_done"  # type: ignore
                return ctx

        pipetree = Pipetree(steps=[AsyncStep(cap=cap, name="async_step")])
        result = await pipetree.run(MockContext(path="/test/path"))
        assert result.result == "async_done"

    @pytest.mark.asyncio
    async def test_pipetree_mixed_sync_async(self) -> None:
        cap1 = Capability(name="sync", requires=set(), provides={"a"})
        cap2 = Capability(name="async", requires={"a"}, provides={"b"})

        class SyncStep(Step):
            def run(self, ctx: Context) -> Context:
                ctx.a = "sync"  # type: ignore
                return ctx

        class AsyncStep(Step):
            async def run(self, ctx: Context) -> Context:
                ctx.b = "async"  # type: ignore
                return ctx

        pipetree = Pipetree(
            steps=[
                SyncStep(cap=cap1, name="sync"),
                AsyncStep(cap=cap2, name="async"),
            ]
        )

        result = await pipetree.run(MockContext(path="/test/path"))
        assert result.a == "sync"
        assert result.b == "async"

    def test_pipetree_repr(self) -> None:
        cap = Capability(name="test", requires=set(), provides=set())

        class TestStep(Step):
            def run(self, ctx: Context) -> Context:
                return ctx

        pipetree = Pipetree(
            steps=[
                TestStep(cap=cap, name="step1"),
                TestStep(cap=cap, name="step2"),
            ]
        )

        repr_str = repr(pipetree)
        assert "step1" in repr_str
        assert "step2" in repr_str

    def test_chain_validation_tracks_initial_context(self) -> None:
        """Later steps can require values from initial context (first step's requires)."""
        # First step requires "path" and "output_path" from initial context
        cap1 = Capability(
            name="load", requires={"path", "output_path"}, provides={"data"}
        )
        # Second step requires "data" (from step1) - no issue
        cap2 = Capability(name="process", requires={"data"}, provides={"result"})
        # Third step requires "output_path" (from initial context, not from any step)
        cap3 = Capability(
            name="save", requires={"result", "output_path"}, provides={"saved"}
        )

        class Step1(Step):
            def run(self, ctx: Context) -> Context:
                ctx.data = "loaded"  # type: ignore
                return ctx

        class Step2(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "processed"  # type: ignore
                return ctx

        class Step3(Step):
            def run(self, ctx: Context) -> Context:
                ctx.saved = True  # type: ignore
                return ctx

        # This should NOT raise - output_path is tracked from first step's requires
        pipetree = Pipetree(
            steps=[
                Step1(cap=cap1, name="load"),
                Step2(cap=cap2, name="process"),
                Step3(cap=cap3, name="save"),
            ]
        )
        assert len(pipetree.steps) == 3
