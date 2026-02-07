"""SQLite progress watcher for monitoring pipeline execution."""

import time
from pathlib import Path
from threading import Event as ThreadEvent
from threading import Thread

from sqlmodel import select

from pipetree.infrastructure.progress.handler import (
    ConsoleProgressHandler,
    ProgressHandler,
)
from pipetree.infrastructure.progress.models import Event, get_session


class SQLiteProgressWatcher:
    """
    Watches a SQLite database for progress events and dispatches them to a handler.

    Usage:
        watcher = SQLiteProgressWatcher(db_path, run_id)
        watcher.start()  # Returns Thread
        # ... pipeline runs ...
        watcher.stop()
    """

    def __init__(
        self,
        db_path: Path,
        run_id: str,
        handler: ProgressHandler | None = None,
        poll_interval: float = 0.05,
    ) -> None:
        """
        Initialize the watcher.

        Args:
            db_path: Path to the SQLite database
            run_id: ID of the run to watch
            handler: Handler for progress events (defaults to ConsoleProgressHandler)
            poll_interval: How often to poll for new events (seconds)
        """
        self.db_path = db_path
        self.run_id = run_id
        self.handler = handler or ConsoleProgressHandler()
        self.poll_interval = poll_interval
        self._stop_event = ThreadEvent()
        self._thread: Thread | None = None

    def start(self) -> Thread:
        """
        Start watching in a background thread.

        Returns:
            The background thread
        """
        self._stop_event.clear()
        self._thread = Thread(target=self._watch_loop, daemon=True)
        self._thread.start()
        return self._thread

    def stop(self, timeout: float = 1.0) -> None:
        """
        Stop watching and wait for the thread to finish.

        Args:
            timeout: How long to wait for the thread to finish
        """
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

    def _watch_loop(self) -> None:
        """Main watch loop that polls the database for events."""
        # Wait for database to be created
        while not self.db_path.exists() and not self._stop_event.is_set():
            time.sleep(0.01)

        if self._stop_event.is_set():
            return

        # Small delay to ensure database is ready
        time.sleep(0.05)

        last_event_id = 0

        while not self._stop_event.is_set():
            try:
                with get_session(self.db_path) as session:
                    # Get new events
                    statement = (
                        select(Event)
                        .where(Event.run_id == self.run_id)
                        .where(Event.id > last_event_id)  # type: ignore[operator]
                        .order_by(Event.id)  # type: ignore[arg-type]
                    )
                    events = session.exec(statement).all()

                    for event in events:
                        last_event_id = event.id or 0
                        self._dispatch_event(event)

            except Exception:
                # Silently ignore errors (database might be busy)
                pass

            time.sleep(self.poll_interval)

        # Cleanup
        self.handler.on_cleanup()

    def _dispatch_event(self, event: Event) -> None:
        """Dispatch an event to the handler."""
        event_type = event.event_type
        step_name = event.step_name or "unknown"

        if event_type == "started":
            self.handler.on_started(step_name)
        elif event_type == "completed":
            self.handler.on_completed(step_name, event.duration_s)
        elif event_type == "failed":
            self.handler.on_failed(step_name, event.error or "unknown error")
        elif event_type == "progress":
            current = event.current or 0
            total = event.total or 0
            self.handler.on_progress(step_name, current, total, event.message)


def watch_progress(
    db_path: Path,
    run_id: str,
    stop_event: ThreadEvent,
    handler: ProgressHandler | None = None,
) -> None:
    """
    Watch progress in the current thread (for backwards compatibility).

    Args:
        db_path: Path to the SQLite database
        run_id: ID of the run to watch
        stop_event: Event to signal when to stop
        handler: Handler for progress events (defaults to ConsoleProgressHandler)
    """
    watcher = SQLiteProgressWatcher(db_path, run_id, handler)
    watcher._stop_event = stop_event
    watcher._watch_loop()
