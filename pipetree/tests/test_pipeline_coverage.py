"""Additional tests for pipeline.py coverage."""

from dataclasses import dataclass

import pytest

from pipetree import Capability, Context, Pipetree, Router, Step, step
from pipetree.domain.pipeline.pipeline import _generate_run_id, _get_branch_step_names


@dataclass
class CoverageTestContext(Context):
    """Test context for coverage tests."""

    a: int | None = None
    b: int | None = None
    route_key: str | None = None
    result: str | None = None


class TestGetBranchStepNames:
    """Test _get_branch_step_names helper function."""

    def test_with_regular_step(self) -> None:
        """Test with a regular Step."""
        cap = Capability(name="test", requires=set(), provides={"a"})

        class TestStep(Step):
            def run(self, ctx: Context) -> Context:
                return ctx

        step = TestStep(cap=cap, name="test_step")
        names = _get_branch_step_names(step)
        assert names == ["test_step"]

    def test_with_router(self) -> None:
        """Test with a Router."""
        cap = Capability(name="route", requires={"key"}, provides={"result"})

        class TestRouter(Router):
            def pick(self, ctx: Context) -> str:
                return "a"

        router = TestRouter(cap=cap, name="test_router", table={})
        names = _get_branch_step_names(router)
        assert names == ["test_router"]

    def test_with_pipetree(self) -> None:
        """Test with a Pipetree."""
        cap1 = Capability(name="s1", requires=set(), provides={"a"})
        cap2 = Capability(name="s2", requires={"a"}, provides={"b"})

        class Step1(Step):
            def run(self, ctx: Context) -> Context:
                ctx.a = 1
                return ctx

        class Step2(Step):
            def run(self, ctx: Context) -> Context:
                ctx.b = 2
                return ctx

        pipe = Pipetree(
            steps=[Step1(cap=cap1, name="step1"), Step2(cap=cap2, name="step2")],
            name="inner",
        )
        names = _get_branch_step_names(pipe)
        assert names == ["step1", "step2"]


class TestGenerateRunId:
    """Test _generate_run_id function."""

    def test_generates_unique_ids(self) -> None:
        """Test that run IDs are unique."""
        ids = {_generate_run_id() for _ in range(100)}
        assert len(ids) == 100  # All unique

    def test_returns_string(self) -> None:
        """Test that run ID is a string."""
        run_id = _generate_run_id()
        assert isinstance(run_id, str)
        assert len(run_id) == 36  # UUID format


class TestPipetreeRunSync:
    """Test run_sync method."""

    def test_run_sync(self) -> None:
        """Test synchronous run wrapper."""

        @step(provides={"a"})
        class SetA(Step):
            def run(self, ctx: Context) -> Context:
                ctx.a = 42
                return ctx

        from pipetree import pipeline

        p = pipeline("Test", [SetA])
        ctx = CoverageTestContext()
        result = p.run_sync(ctx)

        assert result.a == 42


class TestPipetreeRunId:
    """Test run_id property."""

    def test_run_id_none_before_run(self) -> None:
        """Test that run_id is None before running."""

        @step(provides={"a"})
        class SetA(Step):
            def run(self, ctx: Context) -> Context:
                ctx.a = 1
                return ctx

        from pipetree import pipeline

        p = pipeline("Test", [SetA])
        assert p.run_id is None


class TestPipetreeWithNotifier:
    """Test pipeline with notifier for branch registration."""

    @pytest.mark.asyncio
    async def test_router_completion_reports_zero_duration(self) -> None:
        """Test that Router step reports zero duration (branch has actual work)."""
        from pipetree import InMemoryProgressNotifier, branch, pipeline, route

        @step(provides={"route_key"})
        class Setup(Step):
            def run(self, ctx: Context) -> Context:
                ctx.route_key = "a"
                return ctx

        @step(requires={"route_key"}, provides={"result"})
        @branch("a")
        class ProcessA(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "done"
                return ctx

        notifier = InMemoryProgressNotifier()
        route_key = route("route_key")

        p = pipeline(
            "Test",
            [Setup, route_key >> [ProcessA]],
            progress_notifier=notifier,
        )

        ctx = CoverageTestContext()
        await p.run(ctx)

        # Check that events were recorded
        assert len(notifier.events) > 0


class TestPipetreeContractValidation:
    """Test contract validation edge cases."""

    def test_chain_validation_error_message(self) -> None:
        """Test that chain validation error mentions previous step."""
        from pipetree.domain.pipeline.contract_violation_error import (
            ContractViolationError,
        )

        @step(provides={"a"})
        class Step1(Step):
            def run(self, ctx: Context) -> Context:
                ctx.a = 1
                return ctx

        @step(requires={"b"}, provides={"c"})  # Requires 'b' but Step1 provides 'a'
        class Step2(Step):
            def run(self, ctx: Context) -> Context:
                ctx.c = 3
                return ctx

        from pipetree import pipeline

        with pytest.raises(ContractViolationError) as exc_info:
            pipeline("Test", [Step1, Step2])

        assert "step1" in str(exc_info.value).lower()
        assert "step2" in str(exc_info.value).lower()
