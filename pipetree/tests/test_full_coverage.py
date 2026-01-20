"""Tests for achieving 100% coverage on remaining files."""

import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Event as ThreadEvent
from unittest.mock import MagicMock

import pytest

from pipetree import Capability, Context, Pipetree, Step, branch, pipeline, route, step


@dataclass
class CoverageTestContext(Context):
    """Test context for coverage tests."""

    route_key: str | None = None
    value: int | None = None
    result: str | None = None


class TestBuilderPipetreeTarget:
    """Tests for builder.py Pipetree target handling (lines 175-179)."""

    def test_router_with_pipetree_target_capability(self) -> None:
        """Test that router correctly computes capability from Pipetree target."""

        @step(provides={"value"})
        class SetValue(Step):
            def run(self, ctx: Context) -> Context:
                ctx.value = 10
                return ctx

        @step(requires={"value"}, provides={"result"})
        class UseValue(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = f"value is {ctx.value}"
                return ctx

        @step(provides={"route_key"})
        class SetRoute(Step):
            def run(self, ctx: Context) -> Context:
                ctx.route_key = "branch_a"
                return ctx

        # Create inner pipeline for branch_a
        inner_steps = [
            SetValue(cap=SetValue._dsl_capability, name="set_value"),
            UseValue(cap=UseValue._dsl_capability, name="use_value"),
        ]
        inner_pipe = Pipetree(steps=inner_steps, name="inner")

        # Create router with Pipetree as target
        from pipetree.domain.step.router import Router

        class TestRouter(Router):
            def pick(self, ctx: Context) -> str:
                return ctx.route_key

        router_cap = Capability(
            name="route",
            requires={"route_key"},
            provides={"value", "result"},
        )

        router = TestRouter(
            cap=router_cap,
            name="router",
            table={"branch_a": inner_pipe},
        )

        # Create main pipeline
        Pipetree(
            steps=[
                SetRoute(cap=SetRoute._dsl_capability, name="set_route"),
                router,
            ],
            name="main",
        )

        # Verify capability computation
        assert router.cap.requires == {"route_key"}
        assert router.cap.provides == {"value", "result"}

    @pytest.mark.asyncio
    async def test_router_with_empty_pipetree_target(self) -> None:
        """Test router with empty Pipetree target."""

        @step(provides={"route_key"})
        class SetRoute(Step):
            def run(self, ctx: Context) -> Context:
                ctx.route_key = "empty"
                return ctx

        # Create empty inner pipeline
        empty_pipe = Pipetree(steps=[], name="empty")

        from pipetree.domain.step.router import Router

        class TestRouter(Router):
            def pick(self, ctx: Context) -> str:
                return ctx.route_key

        router_cap = Capability(
            name="route",
            requires={"route_key"},
            provides=set(),
        )

        router = TestRouter(
            cap=router_cap,
            name="router",
            table={"empty": empty_pipe},
        )

        ctx = CoverageTestContext(route_key="empty")
        result = await router.run(ctx)
        assert result is not None


class TestPipelineFirstStepRequirements:
    """Tests for pipeline.py line 125 - first step requirements from context."""

    @pytest.mark.asyncio
    async def test_first_step_requirements_from_initial_context(self) -> None:
        """Test that first step's requirements come from initial context."""

        @step(requires={"initial_value"}, provides={"result"})
        class ProcessValue(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = f"processed {ctx.initial_value}"
                return ctx

        @dataclass
        class InitialContext(Context):
            initial_value: str | None = None
            result: str | None = None

        p = pipeline("Test", [ProcessValue])

        ctx = InitialContext(initial_value="test")
        result = await p.run(ctx)
        assert result.result == "processed test"


class TestPipelineRegisterBranchesEdgeCases:
    """Tests for pipeline._register_branches edge cases."""

    @pytest.mark.asyncio
    async def test_register_branches_with_notifier_without_register_branch(
        self,
    ) -> None:
        """Test _register_branches returns early when notifier lacks register_branch."""
        from pipetree.infrastructure.progress import InMemoryProgressNotifier

        @step(provides={"value"})
        class SetValue(Step):
            def run(self, ctx: Context) -> Context:
                ctx.value = 10
                return ctx

        # InMemoryProgressNotifier doesn't have register_branch method
        notifier = InMemoryProgressNotifier()

        p = pipeline("Test", [SetValue], progress_notifier=notifier)

        ctx = CoverageTestContext()
        result = await p.run(ctx)
        assert result.value == 10


class TestSQLiteProgressNotifierEdgeCases:
    """Tests for sqlite_progress_notifier.py edge cases."""

    def test_migrate_schema_when_conn_none(self) -> None:
        """Test _migrate_schema returns early when conn is None."""
        from pipetree.infrastructure.progress import SQLiteProgressNotifier

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            notifier = SQLiteProgressNotifier(db_path)
            notifier.close()

            # _conn is now None, _migrate_schema should return early
            notifier._migrate_schema()  # Should not raise

    def test_register_run_when_conn_none(self) -> None:
        """Test register_run returns run_id when conn is None."""
        from pipetree.infrastructure.progress import SQLiteProgressNotifier

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            notifier = SQLiteProgressNotifier(db_path, run_id="test-run-123")
            notifier.close()

            # Should return the run_id even when conn is None
            result = notifier.register_run("Test", ["step1"])
            assert result == "test-run-123"


class TestSQLiteWatcherExceptionHandling:
    """Tests for sqlite_watcher.py exception handling."""

    def test_watch_loop_handles_database_errors(self) -> None:
        """Test that watch loop silently handles database errors."""
        from pipetree.infrastructure.progress.sqlite_watcher import (
            SQLiteProgressWatcher,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            # Create a mock handler
            handler = MagicMock()

            watcher = SQLiteProgressWatcher(
                db_path=db_path,
                run_id="test-run",
                handler=handler,
                poll_interval=0.01,
            )

            # Create the database file so watcher doesn't wait forever
            db_path.touch()

            # Start and immediately stop
            watcher.start()
            time.sleep(0.05)  # Let it poll once
            watcher.stop()

            # on_cleanup should be called
            handler.on_cleanup.assert_called_once()

    def test_watch_loop_with_corrupted_database(self) -> None:
        """Test that watch loop handles corrupted database gracefully."""
        from pipetree.infrastructure.progress.sqlite_watcher import (
            SQLiteProgressWatcher,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            # Create a corrupted "database" file
            db_path.write_text("not a valid sqlite database")

            handler = MagicMock()

            watcher = SQLiteProgressWatcher(
                db_path=db_path,
                run_id="test-run",
                handler=handler,
                poll_interval=0.01,
            )

            # Start and immediately stop - should not crash
            watcher.start()
            time.sleep(0.05)
            watcher.stop()

            # Should still call cleanup
            handler.on_cleanup.assert_called_once()

    def test_watch_progress_function_with_stop_event_before_db_exists(self) -> None:
        """Test watch_progress function stops when stop_event set before db exists."""
        from pipetree.infrastructure.progress.sqlite_watcher import watch_progress

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            # Don't create db file - test early exit path

            handler = MagicMock()
            stop_event = ThreadEvent()

            # Set stop event immediately
            stop_event.set()

            # Should return quickly without calling cleanup
            # (early exit when stop_event is set while waiting for db)
            watch_progress(db_path, "test-run", stop_event, handler)

            # on_cleanup is NOT called in early exit path
            handler.on_cleanup.assert_not_called()

    def test_watch_progress_function_with_stop_after_db_ready(self) -> None:
        """Test watch_progress function calls cleanup after normal stop."""
        import threading

        from pipetree.infrastructure.progress.sqlite_watcher import watch_progress

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            # Create database file
            db_path.touch()

            handler = MagicMock()
            stop_event = ThreadEvent()

            # Run watch_progress in a thread and stop after a short delay
            def run_watch() -> None:
                watch_progress(db_path, "test-run", stop_event, handler)

            thread = threading.Thread(target=run_watch)
            thread.start()

            # Let it start polling
            time.sleep(0.1)

            # Signal stop
            stop_event.set()
            thread.join(timeout=1.0)

            # Cleanup should be called
            handler.on_cleanup.assert_called_once()


class TestBuilderPipetreeInRouterTable:
    """Tests for builder handling Pipetree in router table (lines 175-179)."""

    def test_build_router_with_pipetree_computes_capability(self) -> None:
        """Test _build_router computes capability from Pipetree target."""
        from pipetree.dsl.builder import _build_router

        @step(provides={"value"})
        class SetValue(Step):
            def run(self, ctx: Context) -> Context:
                ctx.value = 10
                return ctx

        @step(requires={"value"}, provides={"result"})
        @branch("branch_a")
        class UseValue(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "done"
                return ctx

        # Create route marker with step
        route_key = route("route_key")
        marker = route_key >> [UseValue]

        router = _build_router(marker)

        # Verify capability
        assert "route_key" in router.cap.requires
        assert "result" in router.cap.provides

    @pytest.mark.asyncio
    async def test_dsl_pipeline_with_pipetree_branch_target(self) -> None:
        """Test DSL pipeline with Pipetree as branch target runs correctly."""

        @step(provides={"route_key"})
        class SetRoute(Step):
            def run(self, ctx: Context) -> Context:
                ctx.route_key = "process"
                return ctx

        @step(provides={"value"})
        @branch("process")
        class Process(Step):
            def run(self, ctx: Context) -> Context:
                ctx.value = 42
                return ctx

        route_key = route("route_key")

        p = pipeline(
            "Test",
            [
                SetRoute,
                route_key >> [Process],
            ],
        )

        ctx = CoverageTestContext()
        result = await p.run(ctx)
        assert result.value == 42
