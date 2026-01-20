"""Tests for the DSL module."""

from dataclasses import dataclass

import pytest

from pipetree import B, Context, Step, branch, pipeline, route, step
from pipetree.dsl import BranchTarget, RouteMarker
from pipetree.dsl.builder import _get_branch_key, _instantiate_step
from pipetree.dsl.decorators import _to_snake_case


@dataclass
class DSLTestContext(Context):
    """Test context with all fields needed for DSL tests."""

    a: int | None = None
    b: int | None = None
    category: str | None = None
    parts_type: str | None = None
    result: str | None = None
    saved: bool | None = None


class TestSnakeCase:
    def test_simple_conversion(self):
        assert _to_snake_case("LoadPdf") == "load_pdf"
        assert _to_snake_case("ExtractText") == "extract_text"
        assert _to_snake_case("ProcessOps") == "process_ops"

    def test_single_word(self):
        assert _to_snake_case("Step") == "step"
        assert _to_snake_case("Router") == "router"

    def test_already_lowercase(self):
        assert _to_snake_case("step") == "step"

    def test_multiple_caps(self):
        assert _to_snake_case("PDFLoader") == "p_d_f_loader"
        assert _to_snake_case("HTTPClient") == "h_t_t_p_client"


class TestStepDecorator:
    def test_step_decorator_sets_capability(self):
        @step(requires={"path"}, provides={"pdf"})
        class LoadPdf(Step):
            def run(self, ctx: Context) -> Context:
                return ctx

        assert hasattr(LoadPdf, "_dsl_capability")
        assert LoadPdf._dsl_capability.name == "load_pdf"
        assert LoadPdf._dsl_capability.requires == frozenset({"path"})
        assert LoadPdf._dsl_capability.provides == frozenset({"pdf"})

    def test_step_decorator_custom_name(self):
        @step(requires=set(), provides={"a"}, name="custom_name")
        class MyStep(Step):
            def run(self, ctx: Context) -> Context:
                return ctx

        assert MyStep._dsl_capability.name == "custom_name"

    def test_step_decorator_empty_sets(self):
        @step()
        class EmptyStep(Step):
            def run(self, ctx: Context) -> Context:
                return ctx

        assert EmptyStep._dsl_capability.requires == frozenset()
        assert EmptyStep._dsl_capability.provides == frozenset()


class TestRouteMarker:
    def test_route_creation(self):
        r = route("category")
        assert isinstance(r, RouteMarker)
        assert r.key == "category"
        assert r.default is None

    def test_route_with_default(self):
        r = route("category", default="ops")
        assert r.key == "category"
        assert r.default == "ops"

    def test_route_rshift_with_list(self):
        r = route("category") >> [1, 2, 3]
        assert isinstance(r, RouteMarker)
        assert r.branches == [1, 2, 3]

    def test_route_rshift_with_branch_target(self):
        inner = B("parts")
        r = route("category") >> inner
        assert isinstance(r, BranchTarget)
        assert r.key == "category"
        assert r.target == inner


class TestBranchTarget:
    def test_B_creation(self):
        b = B("ops")
        assert isinstance(b, BranchTarget)
        assert b.key == "ops"
        assert b.target is None

    def test_branch_target_rshift(self):
        @step(provides={"a"})
        class MyStep(Step):
            def run(self, ctx):
                return ctx

        b = B("ops") >> MyStep
        assert isinstance(b, BranchTarget)
        assert b.key == "ops"
        assert b.target == MyStep

    def test_chained_rshift(self):
        parts_type = route("parts_type")
        b = B("parts") >> parts_type >> [1, 2]

        assert isinstance(b, BranchTarget)
        assert b.key == "parts"
        # The target should be a RouteMarker with branches
        assert isinstance(b.target, RouteMarker)
        assert b.target.key == "parts_type"
        assert b.target.branches == [1, 2]


class TestPipelineBuilder:
    def test_simple_pipeline(self):
        @step(requires=set(), provides={"a"})
        class Step1(Step):
            def run(self, ctx: Context) -> Context:
                ctx.a = 1
                return ctx

        @step(requires={"a"}, provides={"b"})
        class Step2(Step):
            def run(self, ctx: Context) -> Context:
                ctx.b = 2
                return ctx

        p = pipeline("Test", [Step1, Step2])

        assert p.name == "Test"
        assert len(p.steps) == 2
        assert p.steps[0].name == "step1"
        assert p.steps[1].name == "step2"

    @pytest.mark.asyncio
    async def test_simple_pipeline_runs(self):
        @step(requires=set(), provides={"a"})
        class Step1(Step):
            def run(self, ctx: Context) -> Context:
                ctx.a = 1
                return ctx

        @step(requires={"a"}, provides={"b"})
        class Step2(Step):
            def run(self, ctx: Context) -> Context:
                ctx.b = ctx.a + 1
                return ctx

        p = pipeline("Test", [Step1, Step2])
        ctx = DSLTestContext()
        result = await p.run(ctx)

        assert result.a == 1
        assert result.b == 2

    @pytest.mark.asyncio
    async def test_pipeline_with_routing(self):
        @step(requires=set(), provides={"category"})
        class Categorize(Step):
            def run(self, ctx: Context) -> Context:
                ctx.category = "a"
                return ctx

        @step(requires={"category"}, provides={"result"})
        class ProcessA(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "processed_a"
                return ctx

        @step(requires={"category"}, provides={"result"})
        class ProcessB(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "processed_b"
                return ctx

        category = route("category")
        a = B("a")
        b = B("b")

        p = pipeline(
            "Test",
            [
                Categorize,
                category
                >> [
                    a >> ProcessA,
                    b >> ProcessB,
                ],
            ],
        )

        ctx = DSLTestContext()
        result = await p.run(ctx)

        assert result.category == "a"
        assert result.result == "processed_a"

    @pytest.mark.asyncio
    async def test_pipeline_with_nested_routing(self):
        @step(requires=set(), provides={"category", "parts_type"})
        class Setup(Step):
            def run(self, ctx: Context) -> Context:
                ctx.category = "parts"
                ctx.parts_type = "mechanical"
                return ctx

        @step(requires={"category"}, provides={"result"})
        class ProcessOps(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "ops"
                return ctx

        @step(requires={"parts_type"}, provides={"result"})
        class ProcessMechanical(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "mechanical"
                return ctx

        @step(requires={"parts_type"}, provides={"result"})
        class ProcessElectrical(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "electrical"
                return ctx

        category = route("category")
        parts_type = route("parts_type")
        ops = B("ops")
        parts = B("parts")
        mechanical = B("mechanical")
        electrical = B("electrical")

        p = pipeline(
            "Test",
            [
                Setup,
                category
                >> [
                    ops >> ProcessOps,
                    parts
                    >> parts_type
                    >> [
                        mechanical >> ProcessMechanical,
                        electrical >> ProcessElectrical,
                    ],
                ],
            ],
        )

        ctx = DSLTestContext()
        result = await p.run(ctx)

        assert result.category == "parts"
        assert result.parts_type == "mechanical"
        assert result.result == "mechanical"


class TestDSLReadability:
    """Tests demonstrating the DSL's readability improvements."""

    def test_pipeline_structure_is_visible(self):
        """The pipeline structure should be immediately visible in the code."""

        @step(provides={"a"})
        class LoadPdf(Step):
            def run(self, ctx):
                ctx.a = 1
                return ctx

        @step(requires={"a"}, provides={"b"})
        class ExtractText(Step):
            def run(self, ctx):
                ctx.b = 2
                return ctx

        @step(requires={"b"}, provides={"category"})
        class Categorize(Step):
            def run(self, ctx):
                ctx.category = "ops"
                return ctx

        @step(requires={"category"}, provides={"result"})
        class ProcessOps(Step):
            def run(self, ctx):
                ctx.result = "ops_done"
                return ctx

        @step(requires={"category"}, provides={"result"})
        class ProcessParts(Step):
            def run(self, ctx):
                ctx.result = "parts_done"
                return ctx

        @step(requires={"result"}, provides={"saved"})
        class SaveText(Step):
            def run(self, ctx):
                ctx.saved = True
                return ctx

        # The tree structure is immediately visible:
        category = route("category")
        ops = B("ops")
        parts = B("parts")

        p = pipeline(
            "PDF Pipeline",
            [
                LoadPdf,
                ExtractText,
                Categorize,
                category
                >> [
                    ops >> ProcessOps,
                    parts >> ProcessParts,
                ],
                SaveText,
            ],
        )

        # Verify structure
        assert p.name == "PDF Pipeline"
        assert len(p.steps) == 5  # 4 steps + 1 router
        assert p.steps[0].name == "load_pdf"
        assert p.steps[1].name == "extract_text"
        assert p.steps[2].name == "categorize"
        assert p.steps[3].name == "route_category"  # Auto-generated router
        assert p.steps[4].name == "save_text"


class TestBranchDecorator:
    """Test @branch decorator."""

    def test_branch_decorator_sets_branch_key(self) -> None:
        """Test that @branch sets the _dsl_branch attribute."""

        @step(requires={"a"}, provides={"b"})
        @branch("ops")
        class ProcessOps(Step):
            def run(self, ctx: Context) -> Context:
                return ctx

        assert hasattr(ProcessOps, "_dsl_branch")
        assert ProcessOps._dsl_branch == "ops"


class TestInstantiateStep:
    """Test _instantiate_step helper function."""

    def test_instantiate_step_with_instance(self) -> None:
        """Test that passing an instance returns it as-is."""

        @step(provides={"a"})
        class MyStep(Step):
            def run(self, ctx: Context) -> Context:
                return ctx

        instance = MyStep(cap=MyStep._dsl_capability, name="my_step")
        result = _instantiate_step(instance)
        assert result is instance

    def test_instantiate_step_without_decorator_raises(self) -> None:
        """Test that non-decorated Step class raises ValueError."""

        class PlainStep(Step):
            def run(self, ctx: Context) -> Context:
                return ctx

        with pytest.raises(ValueError) as exc_info:
            _instantiate_step(PlainStep)
        assert "must use @step decorator" in str(exc_info.value)

    def test_instantiate_step_with_invalid_type_raises(self) -> None:
        """Test that non-Step type raises TypeError."""
        with pytest.raises(TypeError) as exc_info:
            _instantiate_step("not a step")
        assert "Expected Step class or instance" in str(exc_info.value)


class TestGetBranchKey:
    """Test _get_branch_key helper function."""

    def test_get_branch_key_from_instance(self) -> None:
        """Test getting branch key from a Step instance."""

        @step(requires={"a"}, provides={"b"})
        @branch("ops")
        class ProcessOps(Step):
            def run(self, ctx: Context) -> Context:
                return ctx

        instance = ProcessOps(cap=ProcessOps._dsl_capability, name="process_ops")
        assert _get_branch_key(instance) == "ops"

    def test_get_branch_key_from_class(self) -> None:
        """Test getting branch key from a Step class."""

        @step(requires={"a"}, provides={"b"})
        @branch("parts")
        class ProcessParts(Step):
            def run(self, ctx: Context) -> Context:
                return ctx

        assert _get_branch_key(ProcessParts) == "parts"

    def test_get_branch_key_returns_none_if_not_set(self) -> None:
        """Test that None is returned if no branch key is set."""

        @step(provides={"a"})
        class NoBranch(Step):
            def run(self, ctx: Context) -> Context:
                return ctx

        assert _get_branch_key(NoBranch) is None


class TestRouteMarkerRepr:
    """Test RouteMarker and BranchTarget repr methods."""

    def test_route_marker_repr(self) -> None:
        """Test RouteMarker string representation."""
        r = route("category")
        assert repr(r) == "route('category')"

    def test_branch_target_repr(self) -> None:
        """Test BranchTarget string representation."""
        b = B("ops")
        assert "ops" in repr(b)


class TestPipelineBuilderEdgeCases:
    """Test edge cases in pipeline building."""

    def test_step_without_branch_in_route_raises(self) -> None:
        """Test that using step without @branch in route raises ValueError."""

        @step(provides={"result"})
        class NoBranchStep(Step):
            def run(self, ctx: Context) -> Context:
                return ctx

        category = route("category")

        with pytest.raises(ValueError) as exc_info:
            pipeline(
                "Test",
                [
                    category >> [NoBranchStep],
                ],
            )
        assert "@branch decorator" in str(exc_info.value)

    def test_step_with_branch_decorator_in_route(self) -> None:
        """Test that step with @branch decorator works in route."""

        @step(provides={"category"})
        class Setup(Step):
            def run(self, ctx: Context) -> Context:
                ctx.category = "ops"
                return ctx

        @step(requires={"category"}, provides={"result"})
        @branch("ops")
        class ProcessOps(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "ops_done"
                return ctx

        @step(requires={"category"}, provides={"result"})
        @branch("parts")
        class ProcessParts(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "parts_done"
                return ctx

        category = route("category")

        p = pipeline(
            "Test",
            [
                Setup,
                category >> [ProcessOps, ProcessParts],
            ],
        )

        assert len(p.steps) == 2
        assert p.steps[1].name == "route_category"

    def test_route_key_not_set_raises(self) -> None:
        """Test that missing route key raises ValueError at runtime."""
        from pipetree.dsl.builder import _build_router

        @step(requires={"category"}, provides={"result"})
        @branch("ops")
        class ProcessOps(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "ops"
                return ctx

        category = route("category")
        marker = category >> [ProcessOps]

        # Build the router directly
        router = _build_router(marker)

        # Create a context with category=None
        ctx = DSLTestContext()

        # The router's pick() should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            router.pick(ctx)
        assert "is not set" in str(exc_info.value)

    def test_nested_route_marker_as_branch(self) -> None:
        """Test nested RouteMarker used as a branch item without explicit key."""

        @step(provides={"category", "sub_type"})
        class Setup(Step):
            def run(self, ctx: Context) -> Context:
                ctx.category = "sub_type"
                ctx.sub_type = "a"
                return ctx

        @step(requires={"sub_type"}, provides={"result"})
        @branch("a")
        class ProcessA(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "a"
                return ctx

        category = route("category")
        sub_type = route("sub_type")

        # Use nested route as branch - route key becomes branch key
        p = pipeline(
            "Test",
            [
                Setup,
                category >> [sub_type >> [ProcessA]],
            ],
        )

        assert len(p.steps) == 2
