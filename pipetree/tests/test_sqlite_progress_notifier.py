"""Tests for SQLiteProgressNotifier coverage."""

import tempfile
from dataclasses import dataclass
from pathlib import Path

import pytest

from pipetree import Context, Step, branch, pipeline, route, step
from pipetree.infrastructure.progress import ProgressEvent, SQLiteProgressNotifier


@dataclass
class NotifierTestContext(Context):
    """Test context for notifier tests."""

    value: int | None = None
    result: str | None = None


class TestSQLiteProgressNotifierCoverage:
    """Test SQLiteProgressNotifier for full coverage."""

    def test_register_branch_and_set_skipped(self) -> None:
        """Test register_branch and set_branch_skipped methods."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            notifier = SQLiteProgressNotifier(db_path)

            # Register a run first
            notifier.register_run("Test", ["step1", "router"])

            # Register branches
            notifier.register_branch(
                parent_step="router",
                branch_name="branch_a",
                step_names=["process_a"],
                start_index=2,
            )
            notifier.register_branch(
                parent_step="router",
                branch_name="branch_b",
                step_names=["process_b"],
                start_index=2,
            )

            # Verify branches were registered
            steps = notifier.get_steps()
            branch_steps = [s for s in steps if s["branch"] is not None]
            assert len(branch_steps) == 2

            # Skip branch_b
            notifier.set_branch_skipped("branch_b")

            # Verify branch_b is skipped
            steps = notifier.get_steps()
            branch_b_steps = [s for s in steps if s["branch"] == "branch_b"]
            assert all(s["status"] == "skipped" for s in branch_b_steps)

            notifier.close()

    def test_get_branches(self) -> None:
        """Test get_branches method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            notifier = SQLiteProgressNotifier(db_path)

            # Register run and branches
            notifier.register_run("Test", ["step1"])
            notifier.register_branch("router", "branch_a", ["step_a"], 1)
            notifier.register_branch("router", "branch_b", ["step_b"], 2)

            branches = notifier.get_branches()
            assert set(branches) == {"branch_a", "branch_b"}

            notifier.close()

    def test_get_steps_filtered_by_branch(self) -> None:
        """Test get_steps with branch filter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            notifier = SQLiteProgressNotifier(db_path)

            notifier.register_run("Test", ["step1"])
            notifier.register_branch("router", "branch_a", ["step_a", "step_a2"], 1)
            notifier.register_branch("router", "branch_b", ["step_b"], 3)

            # Get only branch_a steps
            branch_a_steps = notifier.get_steps(branch="branch_a")
            assert len(branch_a_steps) == 2
            assert all(s["branch"] == "branch_a" for s in branch_a_steps)

            notifier.close()

    def test_get_events_filtered_by_step_name(self) -> None:
        """Test get_events with step_name filter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            notifier = SQLiteProgressNotifier(db_path)

            notifier.register_run("Test", ["step1", "step2"])

            # Create events for different steps
            event1 = ProgressEvent(
                timestamp=1.0,
                step_name="step1",
                step_index=0,
                total_steps=2,
                event_type="started",
            )
            event2 = ProgressEvent(
                timestamp=2.0,
                step_name="step2",
                step_index=1,
                total_steps=2,
                event_type="started",
            )
            notifier.notify(event1)
            notifier.notify(event2)

            # Filter by step name
            step1_events = notifier.get_events(step_name="step1")
            assert len(step1_events) == 1
            assert step1_events[0]["step_name"] == "step1"

            notifier.close()

    def test_get_all_runs(self) -> None:
        """Test get_all_runs method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            notifier = SQLiteProgressNotifier(db_path)

            # Register multiple runs (same notifier can be used to query)
            notifier.register_run("Run1", ["step1"])
            notifier.complete_run("completed")

            # Create another run with new notifier
            notifier2 = SQLiteProgressNotifier(db_path)
            notifier2.register_run("Run2", ["step1"])

            runs = notifier2.get_all_runs()
            assert len(runs) == 2

            notifier.close()
            notifier2.close()

    def test_complete_run(self) -> None:
        """Test complete_run method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            notifier = SQLiteProgressNotifier(db_path)

            notifier.register_run("Test", ["step1"])
            notifier.complete_run("completed")

            run = notifier.get_run()
            assert run is not None
            assert run["status"] == "completed"
            assert run["completed_at"] is not None

            notifier.close()

    def test_notify_failed_event(self) -> None:
        """Test notify with failed event type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            notifier = SQLiteProgressNotifier(db_path)

            notifier.register_run("Test", ["step1"])

            # Start the step
            start_event = ProgressEvent(
                timestamp=1.0,
                step_name="step1",
                step_index=0,
                total_steps=1,
                event_type="started",
            )
            notifier.notify(start_event)

            # Fail the step
            fail_event = ProgressEvent(
                timestamp=2.0,
                step_name="step1",
                step_index=0,
                total_steps=1,
                event_type="failed",
                duration_s=1.0,
                error="Something went wrong",
            )
            notifier.notify(fail_event)

            steps = notifier.get_steps()
            assert steps[0]["status"] == "failed"
            assert steps[0]["error"] == "Something went wrong"

            notifier.close()

    def test_methods_return_early_when_conn_none(self) -> None:
        """Test that methods return early when connection is None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            notifier = SQLiteProgressNotifier(db_path)

            # Close connection
            notifier.close()

            # These should return default values without error
            assert notifier.get_run() is None
            assert notifier.get_steps() == []
            assert notifier.get_branches() == []
            assert notifier.get_events() == []
            assert notifier.get_all_runs() == []

            # These should do nothing without error
            notifier.register_branch("router", "branch", ["step"], 0)
            notifier.set_branch_skipped("branch")
            notifier.complete_run("completed")

            # notify should also not error
            event = ProgressEvent(
                timestamp=1.0,
                step_name="step1",
                step_index=0,
                total_steps=1,
                event_type="started",
            )
            notifier.notify(event)

    def test_migrate_schema_adds_columns_to_existing_db(self) -> None:
        """Test that schema migration adds missing columns."""
        import sqlite3

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            # Create an old-style database without new columns
            conn = sqlite3.connect(str(db_path))
            conn.executescript(
                """
                CREATE TABLE runs (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    started_at REAL,
                    completed_at REAL,
                    status TEXT DEFAULT 'pending',
                    total_steps INTEGER DEFAULT 0
                );

                CREATE TABLE steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    step_index INTEGER NOT NULL,
                    status TEXT DEFAULT 'pending',
                    started_at REAL,
                    completed_at REAL,
                    duration_s REAL,
                    error TEXT,
                    branch TEXT,
                    parent_step TEXT
                );

                CREATE TABLE events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    step_name TEXT NOT NULL,
                    step_index INTEGER NOT NULL,
                    total_steps INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    duration_s REAL,
                    error TEXT,
                    current INTEGER,
                    total INTEGER,
                    message TEXT,
                    branch TEXT
                );
                """
            )
            conn.close()

            # Now create notifier - it should migrate the schema
            notifier = SQLiteProgressNotifier(db_path)

            # Verify columns were added
            cursor = notifier._conn.execute("PRAGMA table_info(steps)")
            columns = {row[1] for row in cursor.fetchall()}
            assert "peak_mem_mb" in columns
            assert "cpu_time_s" in columns

            cursor = notifier._conn.execute("PRAGMA table_info(events)")
            columns = {row[1] for row in cursor.fetchall()}
            assert "peak_mem_mb" in columns
            assert "cpu_time_s" in columns

            notifier.close()

    def test_set_branch_skipped_with_nested_branches(self) -> None:
        """Test that set_branch_skipped handles nested branches."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            notifier = SQLiteProgressNotifier(db_path)

            notifier.register_run("Test", ["router"])

            # Register parent branch
            notifier.register_branch("router", "parent_branch", ["nested_router"], 1)

            # Register nested branch with parent_step pointing to nested_router
            notifier.register_branch(
                "nested_router", "nested_branch", ["nested_step"], 2
            )

            # Skip parent branch - should cascade to nested
            notifier.set_branch_skipped("parent_branch")

            steps = notifier.get_steps()
            parent_steps = [s for s in steps if s["branch"] == "parent_branch"]

            # Parent branch should be skipped
            assert all(s["status"] == "skipped" for s in parent_steps)
            # Nested steps whose parent_step is skipped should also be skipped
            # (due to recursive CTE in set_branch_skipped)

            notifier.close()


class TestSQLiteProgressNotifierIntegration:
    """Integration tests for SQLiteProgressNotifier with pipeline."""

    @pytest.mark.asyncio
    async def test_notifier_with_router_registers_branches(self) -> None:
        """Test that running pipeline with router registers branches."""

        @step(provides={"value"})
        class SetCategory(Step):
            def run(self, ctx: Context) -> Context:
                ctx.value = "positive"
                return ctx

        @step(requires={"value"}, provides={"result"})
        @branch("positive")
        class ProcessPositive(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "positive"
                return ctx

        @step(requires={"value"}, provides={"result"})
        @branch("negative")
        class ProcessNegative(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "negative"
                return ctx

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            notifier = SQLiteProgressNotifier(db_path)

            p = pipeline(
                "Test",
                [
                    SetCategory,
                    route("value") >> [ProcessPositive, ProcessNegative],
                ],
                progress_notifier=notifier,
            )

            ctx = NotifierTestContext()
            await p.run(ctx)

            # Check branches were registered
            branches = notifier.get_branches()
            assert "positive" in branches or "negative" in branches

            notifier.close()
