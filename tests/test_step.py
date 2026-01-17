"""Tests for Step and Router classes."""

import pytest

from ingestion.capability import Capability
from ingestion.step import BaseRouter, BaseStep
from ingestion.types import Ctx


class TestBaseStep:
    def test_step_creation(self) -> None:
        cap = Capability(name="test", requires={"a"}, provides={"b"})

        class TestStep(BaseStep):
            def run(self, ctx: Ctx) -> Ctx:
                ctx["b"] = "value"
                return ctx

        step = TestStep(cap=cap, name="my_step")
        assert step.name == "my_step"
        assert step.cap.name == "test"

    def test_step_run(self) -> None:
        cap = Capability(name="test", requires=set(), provides={"result"})

        class TestStep(BaseStep):
            def run(self, ctx: Ctx) -> Ctx:
                ctx["result"] = 42
                return ctx

        step = TestStep(cap=cap, name="my_step")
        result = step.run({})
        assert result["result"] == 42

    def test_step_repr(self) -> None:
        cap = Capability(name="test_cap", requires=set(), provides=set())

        class TestStep(BaseStep):
            def run(self, ctx: Ctx) -> Ctx:
                return ctx

        step = TestStep(cap=cap, name="my_step")
        repr_str = repr(step)
        assert "TestStep" in repr_str
        assert "my_step" in repr_str
        assert "test_cap" in repr_str


class TestBaseRouter:
    @pytest.mark.asyncio
    async def test_router_picks_correct_route(self) -> None:
        cap = Capability(name="router", requires={"signal"}, provides={"output"})

        class StepA(BaseStep):
            def run(self, ctx: Ctx) -> Ctx:
                ctx["output"] = "A"
                return ctx

        class StepB(BaseStep):
            def run(self, ctx: Ctx) -> Ctx:
                ctx["output"] = "B"
                return ctx

        step_a = StepA(cap=cap, name="step_a")
        step_b = StepB(cap=cap, name="step_b")

        class TestRouter(BaseRouter):
            def pick(self, ctx: Ctx) -> str:
                return "route_a" if ctx.get("signal") == "a" else "route_b"

        router = TestRouter(
            cap=cap,
            name="test_router",
            table={"route_a": step_a, "route_b": step_b},
        )

        ctx_a: Ctx = {"signal": "a"}
        result_a = await router.run(ctx_a)
        assert result_a["output"] == "A"

        ctx_b: Ctx = {"signal": "b"}
        result_b = await router.run(ctx_b)
        assert result_b["output"] == "B"

    @pytest.mark.asyncio
    async def test_router_uses_default(self) -> None:
        cap = Capability(name="router", requires=set(), provides={"output"})

        class DefaultStep(BaseStep):
            def run(self, ctx: Ctx) -> Ctx:
                ctx["output"] = "default"
                return ctx

        default_step = DefaultStep(cap=cap, name="default")

        class TestRouter(BaseRouter):
            def pick(self, ctx: Ctx) -> str:
                return "unknown_route"

        router = TestRouter(
            cap=cap,
            name="test_router",
            table={"known": default_step},
            default="known",
        )

        result = await router.run({})
        assert result["output"] == "default"

    @pytest.mark.asyncio
    async def test_router_raises_on_unknown_route(self) -> None:
        cap = Capability(name="router", requires=set(), provides=set())

        class TestRouter(BaseRouter):
            def pick(self, ctx: Ctx) -> str:
                return "unknown"

        router = TestRouter(cap=cap, name="test_router", table={})

        with pytest.raises(ValueError, match="unknown route"):
            await router.run({})
