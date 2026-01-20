"""Tests for Pipeline notifier integration coverage."""

import tempfile
from dataclasses import dataclass
from pathlib import Path

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
from pipetree.infrastructure.progress import SQLiteProgressNotifier


@dataclass
class NotifierPipelineContext(Context):
    """Test context for pipeline notifier tests."""

    category: str | None = None
    sub_type: str | None = None
    result: str | None = None


class TestPipelineRegisterRun:
    """Test pipeline _register_run method."""

    @pytest.mark.asyncio
    async def test_register_run_with_sqlite_notifier(self) -> None:
        """Test that pipeline registers run with SQLite notifier."""

        @step(provides={"result"})
        class SimpleStep(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "done"
                return ctx

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            notifier = SQLiteProgressNotifier(db_path)

            p = pipeline("Test Pipeline", [SimpleStep], progress_notifier=notifier)

            ctx = NotifierPipelineContext()
            await p.run(ctx)

            # Verify run was registered
            run = notifier.get_run()
            assert run is not None
            assert run["name"] == "Test Pipeline"
            assert run["status"] == "completed"

            # Verify run_id was set
            assert p.run_id is not None

            notifier.close()

    @pytest.mark.asyncio
    async def test_pipeline_gets_run_id_from_notifier(self) -> None:
        """Test that pipeline gets run_id from notifier if available."""

        @step(provides={"result"})
        class SimpleStep(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "done"
                return ctx

        class NotifierWithRunId:
            """Simple notifier with just run_id attribute."""

            def __init__(self):
                self.run_id = "test-run-123"

            def step_started(self, *args):
                pass

            def step_completed(self, *args):
                pass

            def step_failed(self, *args):
                pass

        notifier = NotifierWithRunId()
        p = pipeline("Test", [SimpleStep], progress_notifier=notifier)

        ctx = NotifierPipelineContext()
        await p.run(ctx)

        assert p.run_id == "test-run-123"


class TestPipelineRegisterBranches:
    """Test pipeline _register_branches method."""

    @pytest.mark.asyncio
    async def test_auto_registers_router_branches(self) -> None:
        """Test that pipeline auto-registers branches from Routers."""

        @step(provides={"category"})
        class SetCategory(Step):
            def run(self, ctx: Context) -> Context:
                ctx.category = "a"
                return ctx

        @step(requires={"category"}, provides={"result"})
        @branch("a")
        class ProcessA(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "a_done"
                return ctx

        @step(requires={"category"}, provides={"result"})
        @branch("b")
        class ProcessB(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "b_done"
                return ctx

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            notifier = SQLiteProgressNotifier(db_path)

            category = route("category")
            p = pipeline(
                "Test",
                [SetCategory, category >> [ProcessA, ProcessB]],
                progress_notifier=notifier,
            )

            ctx = NotifierPipelineContext()
            await p.run(ctx)

            # Check branches were registered
            branches = notifier.get_branches()
            assert "a" in branches
            assert "b" in branches

            notifier.close()

    @pytest.mark.asyncio
    async def test_registers_nested_router_branches(self) -> None:
        """Test that pipeline registers branches from nested routers."""

        @step(provides={"category", "sub_type"})
        class Setup(Step):
            def run(self, ctx: Context) -> Context:
                ctx.category = "nested"
                ctx.sub_type = "final"
                return ctx

        @step(requires={"category"}, provides={"result"})
        @branch("simple")
        class ProcessSimple(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "simple"
                return ctx

        @step(requires={"sub_type"}, provides={"result"})
        @branch("final")
        class ProcessFinal(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "final"
                return ctx

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            notifier = SQLiteProgressNotifier(db_path)

            category = route("category")
            sub_type = route("sub_type")
            nested = B("nested")

            p = pipeline(
                "Test",
                [
                    Setup,
                    category >> [ProcessSimple, nested >> sub_type >> [ProcessFinal]],
                ],
                progress_notifier=notifier,
            )

            ctx = NotifierPipelineContext()
            await p.run(ctx)

            # Check all branches were registered
            branches = notifier.get_branches()
            assert "simple" in branches
            assert "nested" in branches

            notifier.close()


class TestPipelineRegisterBranchesWithPipetree:
    """Test branch registration when router target is a Pipetree."""

    @pytest.mark.asyncio
    async def test_registers_branches_from_pipetree_with_router(self) -> None:
        """Test registering branches when Pipetree contains a Router."""

        @step(provides={"category"})
        class SetCategory(Step):
            def run(self, ctx: Context) -> Context:
                ctx.category = "complex"
                return ctx

        @step(requires={"category"}, provides={"sub_type"})
        class SetSubType(Step):
            def run(self, ctx: Context) -> Context:
                ctx.sub_type = "inner_a"
                return ctx

        @step(requires={"sub_type"}, provides={"result"})
        @branch("inner_a")
        class ProcessInnerA(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "inner_a_done"
                return ctx

        @step(requires={"sub_type"}, provides={"result"})
        @branch("inner_b")
        class ProcessInnerB(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "inner_b_done"
                return ctx

        @step(requires={"category"}, provides={"result"})
        @branch("simple")
        class ProcessSimple(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "simple_done"
                return ctx

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            notifier = SQLiteProgressNotifier(db_path)

            # Build inner pipeline with router
            sub_type = route("sub_type")

            # Create a Pipetree with a router inside
            inner_pipe = pipeline(
                "Inner",
                [SetSubType, sub_type >> [ProcessInnerA, ProcessInnerB]],
            )

            # Main router with Pipetree as target
            from pipetree.domain.step.router import Router as BaseRouter

            class MainRouter(BaseRouter):
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

            main_router = MainRouter(
                cap=router_cap,
                name="route_category",
                table={"complex": inner_pipe, "simple": simple_step},
            )

            p = Pipetree(
                steps=[
                    SetCategory(cap=SetCategory._dsl_capability, name="set_category"),
                    main_router,
                ],
                progress_notifier=notifier,
                name="Main",
            )

            ctx = NotifierPipelineContext()
            await p.run(ctx)

            notifier.close()


class TestPipelineCompleteRun:
    """Test pipeline _complete_run method."""

    @pytest.mark.asyncio
    async def test_complete_run_marks_completed(self) -> None:
        """Test that _complete_run marks run as completed."""

        @step(provides={"result"})
        class SimpleStep(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "done"
                return ctx

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            notifier = SQLiteProgressNotifier(db_path)

            p = pipeline("Test", [SimpleStep], progress_notifier=notifier)

            ctx = NotifierPipelineContext()
            await p.run(ctx)

            run = notifier.get_run()
            assert run["status"] == "completed"
            assert run["completed_at"] is not None

            notifier.close()

    @pytest.mark.asyncio
    async def test_complete_run_marks_failed_on_error(self) -> None:
        """Test that _complete_run marks run as failed on error."""

        @step(provides={"result"})
        class FailingStep(Step):
            def run(self, ctx: Context) -> Context:
                raise ValueError("Step failed!")

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            notifier = SQLiteProgressNotifier(db_path)

            p = pipeline("Test", [FailingStep], progress_notifier=notifier)

            ctx = NotifierPipelineContext()
            with pytest.raises(ValueError):
                await p.run(ctx)

            run = notifier.get_run()
            assert run["status"] == "failed"

            notifier.close()
