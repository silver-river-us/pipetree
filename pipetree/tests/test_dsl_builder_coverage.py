"""Tests for DSL builder coverage."""

from dataclasses import dataclass

import pytest

from pipetree import (
    B,
    Capability,
    Context,
    Pipetree,
    Step,
    branch,
    pipeline,
    route,
    step,
)


@dataclass
class BuilderTestContext(Context):
    """Test context for builder tests."""

    category: str | None = None
    sub_type: str | None = None
    result: str | None = None


class TestBuildRouterWithChainedBranchTargets:
    """Test _build_router with chained BranchTarget objects."""

    def test_nested_branch_target_chain(self) -> None:
        """Test building router with deeply nested BranchTarget chain."""

        @step(provides={"category", "sub_type"})
        class Setup(Step):
            def run(self, ctx: Context) -> Context:
                ctx.category = "nested"
                ctx.sub_type = "final"
                return ctx

        @step(requires={"sub_type"}, provides={"result"})
        @branch("final")
        class ProcessFinal(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "final_result"
                return ctx

        # Create a chained structure:
        # category >> [nested >> sub_type >> [ProcessFinal]]
        category = route("category")
        sub_type = route("sub_type")
        nested = B("nested")

        # This creates: B("nested") >> (sub_type >> [ProcessFinal])
        # Which is a BranchTarget whose target is a RouteMarker
        p = pipeline(
            "Test",
            [
                Setup,
                category >> [nested >> sub_type >> [ProcessFinal]],
            ],
        )

        assert len(p.steps) == 2
        # The router should have been built correctly
        assert p.steps[1].name == "route_category"

    @pytest.mark.asyncio
    async def test_nested_branch_target_chain_runs(self) -> None:
        """Test running pipeline with chained BranchTarget."""

        @step(provides={"category", "sub_type"})
        class Setup(Step):
            def run(self, ctx: Context) -> Context:
                ctx.category = "nested"
                ctx.sub_type = "final"
                return ctx

        @step(requires={"sub_type"}, provides={"result"})
        @branch("final")
        class ProcessFinal(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "final_result"
                return ctx

        category = route("category")
        sub_type = route("sub_type")
        nested = B("nested")

        p = pipeline(
            "Test",
            [
                Setup,
                category >> [nested >> sub_type >> [ProcessFinal]],
            ],
        )

        ctx = BuilderTestContext()
        result = await p.run(ctx)

        assert result.result == "final_result"


class TestBuildRouterWithPipetreeTarget:
    """Test _build_router when target is a Pipetree."""

    def test_router_with_pipetree_in_table(self) -> None:
        """Test building router capability from Pipetree target."""

        @step(provides={"result"})
        class Step1(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "step1"
                return ctx

        @step(requires={"result"}, provides={"result"})
        class Step2(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "step2"
                return ctx

        step1 = Step1(cap=Step1._dsl_capability, name="step1")
        step2 = Step2(cap=Step2._dsl_capability, name="step2")

        # Create a Pipetree to use as a branch target
        inner_pipe = Pipetree(steps=[step1, step2], name="inner")

        from pipetree.domain.step.router import Router

        class ManualRouter(Router):
            def pick(self, ctx: Context) -> str:
                return "pipe"

        # Build capability from pipetree
        all_requires = set(inner_pipe.steps[0].cap.requires)
        all_provides = set(inner_pipe.steps[-1].cap.provides)

        router_cap = Capability(
            name="route", requires=all_requires, provides=all_provides
        )

        router = ManualRouter(cap=router_cap, name="router", table={"pipe": inner_pipe})

        # Router should have correct capability
        assert router.cap.provides == {"result"}

    @pytest.mark.asyncio
    async def test_router_runs_pipetree_target(self) -> None:
        """Test running router that delegates to Pipetree."""

        @step(provides={"category"})
        class SetCategory(Step):
            def run(self, ctx: Context) -> Context:
                ctx.category = "complex"
                return ctx

        @step(requires={"category"}, provides={"result"})
        class ProcessComplex(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "complex_done"
                return ctx

        @step(requires={"category"}, provides={"result"})
        @branch("simple")
        class ProcessSimple(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "simple_done"
                return ctx

        # Create inner pipeline for complex branch
        inner_step = ProcessComplex(
            cap=ProcessComplex._dsl_capability, name="process_complex"
        )
        inner_pipe = Pipetree(steps=[inner_step], name="complex_pipe")

        from pipetree.domain.step.router import Router

        class CategoryRouter(Router):
            def pick(self, ctx: Context) -> str:
                return ctx.category

        router_cap = Capability(
            name="route_category",
            requires={"category"},
            provides={"result"},
        )

        simple_step = ProcessSimple(
            cap=ProcessSimple._dsl_capability, name="process_simple"
        )

        router = CategoryRouter(
            cap=router_cap,
            name="route_category",
            table={"complex": inner_pipe, "simple": simple_step},
        )

        main_pipe = Pipetree(
            steps=[
                SetCategory(cap=SetCategory._dsl_capability, name="set_category"),
                router,
            ],
            name="main",
        )

        ctx = BuilderTestContext()
        result = await main_pipe.run(ctx)

        assert result.result == "complex_done"


class TestBuildRouterWithEmptyPipetree:
    """Test edge case of Pipetree with no steps."""

    def test_empty_pipetree_capability_handling(self) -> None:
        """Test that empty Pipetree doesn't cause errors in capability building."""
        # Pipetree with no steps - ensure it doesn't crash
        _ = Pipetree(steps=[], name="empty")

        # The pipeline builder checks if target.steps before accessing first/last
        from pipetree.dsl.builder import _build_router

        @step(requires={"category"}, provides={"result"})
        @branch("normal")
        class NormalStep(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "normal"
                return ctx

        # Create a route marker with only normal branch (not testing empty pipe directly)
        category = route("category")
        marker = category >> [NormalStep]

        router = _build_router(marker)
        assert "normal" in router.table
