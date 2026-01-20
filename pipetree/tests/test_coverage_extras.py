"""Additional tests for coverage gaps in various modules."""

import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from pipetree import Capability, Context, Router, Step

# =============================================================================
# Context coverage tests
# =============================================================================


@dataclass
class CoverageContext(Context):
    """Test context with various field types."""

    name: str | None = None
    count: int = 0
    items: list[str] = field(default_factory=list)


class TestContextCoverage:
    """Test Context class coverage."""

    def test_keys_returns_non_none_fields(self) -> None:
        """Test that keys() returns only non-None fields."""
        ctx = CoverageContext(name="test", count=5)
        keys = ctx.keys()
        assert "name" in keys
        assert "count" in keys
        # items has default factory, should be in keys
        assert "items" in keys

    def test_keys_excludes_none_values(self) -> None:
        """Test that keys() excludes None values."""
        ctx = CoverageContext()  # name is None
        keys = ctx.keys()
        assert "name" not in keys

    def test_report_progress_without_notifier(self) -> None:
        """Test report_progress when no notifier is set."""
        ctx = CoverageContext()
        # Should not raise even without notifier
        ctx.report_progress(5, 10, "test message")


# =============================================================================
# Router coverage tests
# =============================================================================


class TestRouterCoverage:
    """Test Router class coverage."""

    def test_router_with_default_when_key_not_in_table(self) -> None:
        """Test router uses default when key not in routing table."""
        cap = Capability(name="route", requires={"key"}, provides={"result"})

        class Step1(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "from_default"
                return ctx

        step1 = Step1(
            cap=Capability(name="s1", requires=set(), provides={"result"}),
            name="default_step",
        )

        class TestRouter(Router):
            def pick(self, ctx: Context) -> str:
                return "unknown_key"  # Not in table

        router = TestRouter(
            cap=cap,
            name="test_router",
            table={"known_key": step1},
            default="known_key",
        )

        @dataclass
        class RouteContext(Context):
            key: str = "test"
            result: str | None = None

        ctx = RouteContext()

        # When pick returns unknown key, should use default
        import asyncio

        result = asyncio.run(router.run(ctx))
        assert result.result == "from_default"

    def test_router_no_default_raises_on_unknown(self) -> None:
        """Test router raises when no default and key unknown."""
        cap = Capability(name="route", requires={"key"}, provides={"result"})

        class DummyStep(Step):
            def run(self, ctx: Context) -> Context:
                return ctx

        dummy = DummyStep(
            cap=Capability(name="d", requires=set(), provides=set()), name="dummy"
        )

        class UnknownRouter(Router):
            def pick(self, ctx: Context) -> str:
                return "unknown_key"

        router = UnknownRouter(
            cap=cap, name="test_router", table={"known": dummy}, default=None
        )

        @dataclass
        class RouteContext(Context):
            key: str = "test"

        ctx = RouteContext()

        with pytest.raises(ValueError, match="unknown route"):
            import asyncio

            asyncio.run(router.run(ctx))

    def test_router_get_unselected_branches(self) -> None:
        """Test _get_unselected_branches method."""
        cap = Capability(name="route", requires=set(), provides={"result"})

        class DummyStep(Step):
            def run(self, ctx: Context) -> Context:
                return ctx

        step_a = DummyStep(
            cap=Capability(name="a", requires=set(), provides=set()), name="a"
        )
        step_b = DummyStep(
            cap=Capability(name="b", requires=set(), provides=set()), name="b"
        )
        step_c = DummyStep(
            cap=Capability(name="c", requires=set(), provides=set()), name="c"
        )

        from typing import ClassVar

        class BranchRouter(Router):
            branch_outputs: ClassVar[dict[str, list[str]]] = {
                "a": ["out_a"],
                "b": ["out_b"],
                "c": ["out_c"],
            }

            def pick(self, ctx: Context) -> str:
                return "a"

        router = BranchRouter(
            cap=cap, name="router", table={"a": step_a, "b": step_b, "c": step_c}
        )

        # When "a" is selected, b and c are unselected
        unselected = router._get_unselected_branches("a")
        assert set(unselected) == {"b", "c"}


# =============================================================================
# FileCheckpointStore coverage tests
# =============================================================================


class TestFileCheckpointStoreCoverage:
    """Test FileCheckpointStore coverage."""

    def test_load_returns_none_for_missing_file(self) -> None:
        """Test load returns None for non-existent checkpoint."""
        from pipetree import FileCheckpointStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileCheckpointStore(Path(tmpdir))
            result = store.load("nonexistent_doc")
            assert result is None

    def test_delete_nonexistent_does_not_raise(self) -> None:
        """Test deleting nonexistent checkpoint doesn't raise."""
        from pipetree import FileCheckpointStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileCheckpointStore(Path(tmpdir))
            # Should not raise
            store.delete("nonexistent_doc")


# =============================================================================
# FileProgressNotifier coverage tests
# =============================================================================


class TestFileProgressNotifierCoverage:
    """Test FileProgressNotifier coverage."""

    def test_notify_with_progress_event(self) -> None:
        """Test notify with a progress event."""
        from pipetree import FileProgressNotifier, ProgressEvent

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "progress.csv"
            notifier = FileProgressNotifier(csv_path)

            event = ProgressEvent(
                timestamp=1234567890.0,
                step_name="test_step",
                step_index=0,
                total_steps=1,
                event_type="progress",
                current=5,
                total=10,
                message="test progress",
            )
            notifier.notify(event)

            # Verify file was written
            assert csv_path.exists()
            content = csv_path.read_text()
            assert "test_step" in content
            assert "progress" in content


# =============================================================================
# SQLiteWatcher coverage tests
# =============================================================================


class TestSQLiteWatcherCoverage:
    """Test SQLiteProgressWatcher coverage."""

    def test_watch_progress_function_stops_early_if_db_missing(self) -> None:
        """Test watch_progress stops if DB never appears and stop_event set."""
        from threading import Event

        from pipetree import watch_progress

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "nonexistent.db"
            stop_event = Event()

            # Set stop event immediately
            stop_event.set()

            # Should return quickly without error
            watch_progress(db_path, "run-123", stop_event)
