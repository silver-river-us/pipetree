"""Tests for error handling and recovery scenarios."""

import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import pytest

from pipetree import (
    Capability,
    Context,
    Pipetree,
    Router,
    Step,
    branch,
    pipeline,
    route,
    step,
)


@dataclass
class RemainingCoverageContext(Context):
    """Test context for remaining coverage tests."""

    category: str | None = None
    sub_category: str | None = None
    deep_category: str | None = None
    result: str | None = None


# =============================================================================
# FileCheckpointStore coverage - lines 30-31 (JSON decode error handling)
# =============================================================================


class TestFileCheckpointStoreErrorHandling:
    """Test FileCheckpointStore error handling."""

    def test_load_returns_none_for_invalid_json(self) -> None:
        """Test that load() returns None when file contains invalid JSON."""
        from pipetree import FileCheckpointStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileCheckpointStore(Path(tmpdir))

            # Create a file with invalid JSON using the correct path
            # FileCheckpointStore uses "{doc_id}.checkpoint.json" format
            checkpoint_path = Path(tmpdir) / "test_doc.checkpoint.json"
            checkpoint_path.write_text("{ invalid json }")

            result = store.load("test_doc")
            assert result is None

    def test_load_returns_none_for_empty_file(self) -> None:
        """Test that load() returns None for empty file (JSONDecodeError)."""
        from pipetree import FileCheckpointStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileCheckpointStore(Path(tmpdir))

            # Create an empty file using the correct path format
            checkpoint_path = Path(tmpdir) / "empty_doc.checkpoint.json"
            checkpoint_path.write_text("")

            result = store.load("empty_doc")
            assert result is None


# =============================================================================
# FileProgressNotifier coverage - line 50 (early return when writer is None)
# =============================================================================


class TestFileProgressNotifierEdgeCases:
    """Test FileProgressNotifier edge cases."""

    def test_notify_after_close_does_nothing(self) -> None:
        """Test that notify does nothing when notifier is closed."""
        from pipetree import FileProgressNotifier, ProgressEvent

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "progress.csv"
            notifier = FileProgressNotifier(csv_path)

            # Close the notifier
            notifier.close()

            # Create an event
            event = ProgressEvent(
                timestamp=1.0,
                step_name="test_step",
                step_index=0,
                total_steps=1,
                event_type="started",
            )

            # Should not raise even after close
            notifier.notify(event)


# =============================================================================
# SQLiteProgressWatcher coverage - lines 78, 104-106 (watch loop edge cases)
# =============================================================================


class TestSQLiteProgressWatcherEdgeCases:
    """Test SQLiteProgressWatcher edge cases."""

    def test_watcher_waits_for_db_creation(self) -> None:
        """Test that watcher waits for database to be created."""
        from pipetree import SQLiteProgressNotifier, SQLiteProgressWatcher

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "delayed.db"

            # Start watcher before DB exists
            watcher = SQLiteProgressWatcher(db_path, "test-run")
            watcher.start()

            # Give it a moment to start waiting
            time.sleep(0.05)

            # Now create the DB
            notifier = SQLiteProgressNotifier(db_path, run_id="test-run")
            notifier.register_run("Test", ["step1"])

            # Give watcher time to detect the DB
            time.sleep(0.1)

            watcher.stop()
            notifier.close()

    def test_watcher_handles_db_errors_gracefully(self) -> None:
        """Test that watcher handles database errors gracefully."""
        from pipetree import SQLiteProgressNotifier, SQLiteProgressWatcher

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            # Create the database first
            notifier = SQLiteProgressNotifier(db_path, run_id="test-run")
            notifier.register_run("Test", ["step1"])

            # Start watcher
            watcher = SQLiteProgressWatcher(db_path, "test-run")
            watcher.start()

            # The watcher should handle any errors gracefully
            time.sleep(0.15)

            watcher.stop()
            notifier.close()


# =============================================================================
# DSL Builder coverage - lines 128-138 (chained BranchTarget unwrapping)
# =============================================================================


class TestDSLBuilderChainedBranchTarget:
    """Test DSL builder with deeply chained BranchTarget."""

    def test_deeply_chained_branch_target_with_step(self) -> None:
        """Test building router with B() >> B() >> step pattern.

        This tests line 130 in builder.py: the while loop that unwraps
        chained BranchTargets to find the final target.
        """

        @step(provides={"result"})
        class FinalStep(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "final"
                return ctx

        from pipetree.dsl.builder import _build_router
        from pipetree.dsl.markers import BranchTarget, RouteMarker

        # Create a triple-nested BranchTarget chain:
        # B("a") -> B("b") -> B("c") -> FinalStep
        # This triggers the while loop on line 130
        innermost = BranchTarget("c")
        innermost.target = FinalStep

        middle = BranchTarget("b")
        middle.target = innermost

        outer = BranchTarget("a")
        outer.target = middle

        marker = RouteMarker("category")
        marker.branches = [outer]

        router = _build_router(marker)

        # The router should have unwrapped the chain correctly
        assert "a" in router.table

    def test_chained_branch_target_with_route_marker(self) -> None:
        """Test building router with B() >> B() >> RouteMarker pattern."""

        @step(requires={"deep_category"}, provides={"result"})
        @branch("deep_a")
        class DeepA(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "deep_a"
                return ctx

        # Create: B("outer") >> (B("inner") >> (route >> [DeepA]))
        deep_route = route("deep_category") >> [DeepA]

        from pipetree.dsl.markers import BranchTarget, RouteMarker

        inner_branch = BranchTarget("inner")
        inner_branch.target = deep_route  # B("inner") -> RouteMarker

        outer_branch = BranchTarget("outer")
        outer_branch.target = inner_branch  # B("outer") -> B("inner") -> RouteMarker

        from pipetree.dsl.builder import _build_router

        marker = RouteMarker("category")
        marker.branches = [outer_branch]

        router = _build_router(marker)

        assert "outer" in router.table


# =============================================================================
# DSL Builder coverage - lines 175-179 (Pipetree target in router table)
# Note: These lines are covered when a Pipetree is manually added to a router
# table and the capability is computed. This happens through direct Router
# construction, not through the DSL builder.
# =============================================================================


class TestPipetreeTargetCapability:
    """Test capability computation with Pipetree target."""

    @pytest.mark.asyncio
    async def test_pipetree_nested_in_router(self) -> None:
        """Test a router that has a Pipetree as one of its targets."""

        @step(provides={"result"})
        class Step1(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "step1"
                return ctx

        @step(requires={"result"}, provides={"result"})
        class Step2(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "step2_done"
                return ctx

        # Create inner pipeline
        step1 = Step1(cap=Step1._dsl_capability, name="step1")
        step2 = Step2(cap=Step2._dsl_capability, name="step2")
        inner_pipe = Pipetree(steps=[step1, step2], name="inner")

        # Create a simple step for another branch
        @step(requires={"category"}, provides={"result"})
        class SimpleStep(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "simple_done"
                return ctx

        simple_step = SimpleStep(cap=SimpleStep._dsl_capability, name="simple_step")

        # Create router with Pipetree and Step targets
        class TestRouter(Router):
            def pick(self, ctx: Context) -> str:
                return ctx.category

        # Router capability needs to account for Pipetree
        router_cap = Capability(
            name="route",
            requires={"category"},
            provides={"result"},
        )

        router = TestRouter(
            cap=router_cap,
            name="router",
            table={"pipe": inner_pipe, "simple": simple_step},
        )

        # Create main pipeline
        @step(provides={"category"})
        class SetCategory(Step):
            def run(self, ctx: Context) -> Context:
                ctx.category = "pipe"
                return ctx

        set_cat = SetCategory(cap=SetCategory._dsl_capability, name="set_category")

        main_pipe = Pipetree(steps=[set_cat, router], name="main")

        ctx = RemainingCoverageContext()
        result = await main_pipe.run(ctx)

        assert result.result == "step2_done"


# =============================================================================
# Pipeline coverage - line 125 (notifier without register_branch)
# =============================================================================


class TestPipelineWithoutBranchRegistration:
    """Test pipeline with notifier that doesn't support branch registration."""

    @pytest.mark.asyncio
    async def test_pipeline_works_without_register_branch(self) -> None:
        """Test that pipeline works when notifier doesn't have register_branch."""

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

        # Create a simple notifier without register_branch
        class SimpleNotifier:
            def step_started(self, *args):
                pass

            def step_completed(self, *args):
                pass

            def step_failed(self, *args):
                pass

        notifier = SimpleNotifier()

        p = pipeline(
            "Test",
            [SetCategory, route("category") >> [ProcessA, ProcessB]],
            progress_notifier=notifier,
        )

        ctx = RemainingCoverageContext()
        result = await p.run(ctx)

        assert result.result == "a_done"
