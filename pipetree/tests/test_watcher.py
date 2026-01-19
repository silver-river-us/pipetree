"""Tests for SQLiteProgressWatcher."""

import tempfile
import time
from pathlib import Path
from threading import Event

from pipetree import SQLiteProgressNotifier
from pipetree.infrastructure.progress.watcher import (
    ConsoleProgressHandler,
    SQLiteProgressWatcher,
    watch_progress,
)


class MockProgressHandler:
    """Mock handler for testing."""

    def __init__(self) -> None:
        self.started: list[str] = []
        self.completed: list[tuple[str, float | None]] = []
        self.failed: list[tuple[str, str]] = []
        self.progress: list[tuple[str, int, int, str | None]] = []
        self.cleanup_called = False

    def on_started(self, step_name: str) -> None:
        self.started.append(step_name)

    def on_completed(self, step_name: str, duration_s: float | None) -> None:
        self.completed.append((step_name, duration_s))

    def on_failed(self, step_name: str, error: str) -> None:
        self.failed.append((step_name, error))

    def on_progress(
        self, step_name: str, current: int, total: int, message: str | None
    ) -> None:
        self.progress.append((step_name, current, total, message))

    def on_cleanup(self) -> None:
        self.cleanup_called = True


class TestConsoleProgressHandler:
    def test_handler_implements_protocol(self) -> None:
        """Test that ConsoleProgressHandler implements ProgressHandler protocol."""
        handler = ConsoleProgressHandler()
        # Just verify the methods exist and are callable
        assert callable(handler.on_started)
        assert callable(handler.on_completed)
        assert callable(handler.on_failed)
        assert callable(handler.on_progress)
        assert callable(handler.on_cleanup)


class TestSQLiteProgressWatcher:
    def test_watcher_creation(self) -> None:
        """Test watcher can be created with db_path and run_id."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            watcher = SQLiteProgressWatcher(db_path, "run-123")
            assert watcher.db_path == db_path
            assert watcher.run_id == "run-123"

    def test_watcher_with_custom_handler(self) -> None:
        """Test watcher accepts custom handler."""
        handler = MockProgressHandler()
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            watcher = SQLiteProgressWatcher(db_path, "run-123", handler=handler)
            assert watcher.handler is handler

    def test_watcher_start_stop(self) -> None:
        """Test watcher can start and stop."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            # Create database with notifier
            notifier = SQLiteProgressNotifier(db_path)
            run_id = notifier.register_run("test", ["step1"])

            watcher = SQLiteProgressWatcher(db_path, run_id)
            thread = watcher.start()

            # Thread should be alive
            assert thread.is_alive()

            # Stop should terminate thread
            watcher.stop(timeout=2.0)
            assert not thread.is_alive()

            notifier.close()

    def test_watcher_receives_events(self) -> None:
        """Test watcher receives and dispatches events."""
        handler = MockProgressHandler()

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            # Create database and run
            notifier = SQLiteProgressNotifier(db_path)
            run_id = notifier.register_run("test", ["step1", "step2"])

            # Start watcher
            watcher = SQLiteProgressWatcher(
                db_path, run_id, handler=handler, poll_interval=0.01
            )
            watcher.start()

            # Give watcher time to start
            time.sleep(0.1)

            # Emit some events
            notifier.step_started("step1", 0, 2)
            time.sleep(0.05)  # Give time to poll

            notifier.step_completed("step1", 0, 2, 1.5)
            time.sleep(0.05)

            notifier.step_started("step2", 1, 2)
            time.sleep(0.05)

            notifier.step_failed("step2", 1, 2, 0.5, "test error")
            time.sleep(0.05)

            # Stop watcher
            watcher.stop()

            # Verify handler received events
            assert "step1" in handler.started
            assert ("step1", 1.5) in handler.completed
            assert "step2" in handler.started
            assert ("step2", "test error") in handler.failed
            assert handler.cleanup_called

            notifier.close()

    def test_watcher_receives_progress_events(self) -> None:
        """Test watcher receives progress events."""
        handler = MockProgressHandler()

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            # Create database and run
            notifier = SQLiteProgressNotifier(db_path)
            run_id = notifier.register_run("test", ["step1"])

            # Start watcher
            watcher = SQLiteProgressWatcher(
                db_path, run_id, handler=handler, poll_interval=0.01
            )
            watcher.start()

            # Give watcher time to start
            time.sleep(0.1)

            # Emit progress events
            notifier.step_started("step1", 0, 1)
            time.sleep(0.05)

            notifier.step_progress("step1", 0, 1, 1, 10, "Processing item 1")
            time.sleep(0.05)

            notifier.step_progress("step1", 0, 1, 5, 10, "Processing item 5")
            time.sleep(0.05)

            # Stop watcher
            watcher.stop()

            # Verify progress events
            assert len(handler.progress) >= 2

            notifier.close()


class TestWatchProgressFunction:
    def test_watch_progress_with_stop_event(self) -> None:
        """Test the backwards-compatible watch_progress function."""
        handler = MockProgressHandler()

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            # Create database and run
            notifier = SQLiteProgressNotifier(db_path)
            run_id = notifier.register_run("test", ["step1"])

            stop_event = Event()

            # Run watch_progress in a thread
            from threading import Thread

            thread = Thread(
                target=watch_progress, args=(db_path, run_id, stop_event, handler)
            )
            thread.start()

            # Give watcher time to start
            time.sleep(0.1)

            # Emit some events
            notifier.step_started("step1", 0, 1)
            time.sleep(0.05)

            # Stop
            stop_event.set()
            thread.join(timeout=2.0)

            # Verify handler received event
            assert "step1" in handler.started

            notifier.close()
