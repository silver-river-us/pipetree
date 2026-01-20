"""Tests for Router class coverage."""

import tempfile
from dataclasses import dataclass
from pathlib import Path

import pytest

from pipetree import Capability, Context, Pipetree, Router, Step
from pipetree.infrastructure.progress import SQLiteProgressNotifier


@dataclass
class RouterTestContext(Context):
    """Test context for router tests."""

    route_key: str | None = None
    result: str | None = None
    branch_a_out: dict | None = None
    branch_b_out: dict | None = None


class TestRouterWithNotifier:
    """Test Router with progress notifier."""

    @pytest.mark.asyncio
    async def test_router_marks_branches_skipped(self) -> None:
        """Test that router marks unselected branches as skipped."""
        cap = Capability(name="route", requires={"route_key"}, provides={"result"})

        class StepA(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "a"
                return ctx

        class StepB(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "b"
                return ctx

        step_a = StepA(
            cap=Capability(name="a", requires=set(), provides={"result"}), name="step_a"
        )
        step_b = StepB(
            cap=Capability(name="b", requires=set(), provides={"result"}), name="step_b"
        )

        class TestRouter(Router):
            def pick(self, ctx: Context) -> str:
                return ctx.route_key

        router = TestRouter(
            cap=cap,
            name="test_router",
            table={"a": step_a, "b": step_b},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            notifier = SQLiteProgressNotifier(db_path)
            notifier.register_run("Test", ["test_router"])
            notifier.register_branch("test_router", "a", ["step_a"], 1)
            notifier.register_branch("test_router", "b", ["step_b"], 2)

            ctx = RouterTestContext(route_key="a")
            ctx._notifier = notifier
            ctx._step_index = 0
            ctx._total_steps = 1

            await router.run(ctx)

            # Branch b should be skipped
            steps = notifier.get_steps()
            branch_b = [s for s in steps if s["branch"] == "b"]
            assert len(branch_b) > 0
            assert branch_b[0]["status"] == "skipped"

            notifier.close()


class TestRouterWithPipetreeTarget:
    """Test Router with Pipetree as target."""

    @pytest.mark.asyncio
    async def test_router_delegates_to_pipetree(self) -> None:
        """Test that router delegates to Pipetree target."""

        class Step1(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "step1"
                return ctx

        class Step2(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "step2"
                return ctx

        step1 = Step1(
            cap=Capability(name="s1", requires=set(), provides={"result"}), name="step1"
        )
        step2 = Step2(
            cap=Capability(name="s2", requires=set(), provides={"result"}), name="step2"
        )

        inner_pipe = Pipetree(steps=[step1, step2], name="inner")

        class PipeRouter(Router):
            def pick(self, ctx: Context) -> str:
                return "pipe"

        router = PipeRouter(
            cap=Capability(name="route", requires=set(), provides={"result"}),
            name="router",
            table={"pipe": inner_pipe},
        )

        ctx = RouterTestContext()
        result = await router.run(ctx)

        assert result.result == "step2"


class TestRouterWithNestedRouter:
    """Test Router with another Router as target."""

    @pytest.mark.asyncio
    async def test_router_delegates_to_nested_router(self) -> None:
        """Test that router delegates to nested Router target."""

        class FinalStep(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "final"
                return ctx

        final_step = FinalStep(
            cap=Capability(name="final", requires=set(), provides={"result"}),
            name="final",
        )

        class InnerRouter(Router):
            def pick(self, ctx: Context) -> str:
                return "final"

        inner_router = InnerRouter(
            cap=Capability(name="inner", requires=set(), provides={"result"}),
            name="inner_router",
            table={"final": final_step},
        )

        class OuterRouter(Router):
            def pick(self, ctx: Context) -> str:
                return "inner"

        outer_router = OuterRouter(
            cap=Capability(name="outer", requires=set(), provides={"result"}),
            name="outer_router",
            table={"inner": inner_router},
        )

        ctx = RouterTestContext()
        result = await outer_router.run(ctx)

        assert result.result == "final"


class TestRouterAsyncStep:
    """Test Router with async step."""

    @pytest.mark.asyncio
    async def test_router_handles_async_step(self) -> None:
        """Test that router properly awaits async steps."""

        class AsyncStep(Step):
            async def run(self, ctx: Context) -> Context:
                import asyncio

                await asyncio.sleep(0.01)
                ctx.result = "async_result"
                return ctx

        async_step = AsyncStep(
            cap=Capability(name="async", requires=set(), provides={"result"}),
            name="async_step",
        )

        class AsyncRouter(Router):
            def pick(self, ctx: Context) -> str:
                return "async"

        router = AsyncRouter(
            cap=Capability(name="route", requires=set(), provides={"result"}),
            name="router",
            table={"async": async_step},
        )

        ctx = RouterTestContext()
        result = await router.run(ctx)

        assert result.result == "async_result"


class TestRouterStepFailure:
    """Test Router handling step failure."""

    @pytest.mark.asyncio
    async def test_router_reports_step_failure(self) -> None:
        """Test that router reports failure when step raises."""

        class FailingStep(Step):
            def run(self, ctx: Context) -> Context:
                raise ValueError("Step failed!")

        failing_step = FailingStep(
            cap=Capability(name="fail", requires=set(), provides={"result"}),
            name="failing_step",
        )

        class FailRouter(Router):
            def pick(self, ctx: Context) -> str:
                return "fail"

        router = FailRouter(
            cap=Capability(name="route", requires=set(), provides={"result"}),
            name="router",
            table={"fail": failing_step},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            notifier = SQLiteProgressNotifier(db_path)
            notifier.register_run("Test", ["router"])

            ctx = RouterTestContext()
            ctx._notifier = notifier
            ctx._step_index = 0
            ctx._total_steps = 1

            with pytest.raises(ValueError, match="Step failed!"):
                await router.run(ctx)

            notifier.close()


class TestRouterBranchOutputs:
    """Test Router branch_outputs initialization."""

    @pytest.mark.asyncio
    async def test_router_initializes_unselected_outputs(self) -> None:
        """Test that router sets empty dicts for unselected branch outputs."""

        class StepA(Step):
            def run(self, ctx: Context) -> Context:
                ctx.branch_a_out = {"data": "a"}
                return ctx

        class StepB(Step):
            def run(self, ctx: Context) -> Context:
                ctx.branch_b_out = {"data": "b"}
                return ctx

        step_a = StepA(
            cap=Capability(name="a", requires=set(), provides={"branch_a_out"}),
            name="step_a",
        )
        step_b = StepB(
            cap=Capability(name="b", requires=set(), provides={"branch_b_out"}),
            name="step_b",
        )

        from typing import ClassVar

        class BranchOutputRouter(Router):
            branch_outputs: ClassVar[dict[str, list[str]]] = {
                "a": ["branch_a_out"],
                "b": ["branch_b_out"],
            }

            def pick(self, ctx: Context) -> str:
                return "a"

        router = BranchOutputRouter(
            cap=Capability(
                name="route", requires=set(), provides={"branch_a_out", "branch_b_out"}
            ),
            name="router",
            table={"a": step_a, "b": step_b},
        )

        ctx = RouterTestContext()
        result = await router.run(ctx)

        # Selected branch should have real data
        assert result.branch_a_out == {"data": "a"}
        # Unselected branch should have empty dict
        assert result.branch_b_out == {}
