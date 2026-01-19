"""SQLite-based progress notifier for persistent event storage."""

import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

from pipetree.infrastructure.progress.progress_notifier import (
    ProgressEvent,
    ProgressNotifier,
)


class SQLiteProgressNotifier(ProgressNotifier):
    """
    Stores progress events in a SQLite database.

    Features:
    - Persistent storage of all pipeline runs
    - Run tracking with unique run_id
    - Step metadata registration before execution
    - Query-friendly schema for visualization
    """

    def __init__(self, db_path: Path | str, run_id: str | None = None) -> None:
        self.db_path = Path(db_path)
        self.run_id = run_id or str(uuid.uuid4())
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                name TEXT,
                started_at REAL,
                completed_at REAL,
                status TEXT DEFAULT 'pending',
                total_steps INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                name TEXT NOT NULL,
                step_index INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                started_at REAL,
                completed_at REAL,
                duration_s REAL,
                peak_mem_mb REAL,
                error TEXT,
                branch TEXT,
                parent_step TEXT,
                FOREIGN KEY (run_id) REFERENCES runs(id)
            );

            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                timestamp REAL NOT NULL,
                step_name TEXT NOT NULL,
                step_index INTEGER NOT NULL,
                total_steps INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                duration_s REAL,
                peak_mem_mb REAL,
                error TEXT,
                current INTEGER,
                total INTEGER,
                message TEXT,
                branch TEXT,
                FOREIGN KEY (run_id) REFERENCES runs(id)
            );

            CREATE INDEX IF NOT EXISTS idx_events_run_id ON events(run_id);
            CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
            CREATE INDEX IF NOT EXISTS idx_steps_run_id ON steps(run_id);
            CREATE INDEX IF NOT EXISTS idx_steps_branch ON steps(branch);
            """
        )
        self._conn.commit()

        # Migrate existing tables to add peak_mem_mb column if missing
        self._migrate_add_peak_mem_mb()

    def _migrate_add_peak_mem_mb(self) -> None:
        """Add peak_mem_mb column to existing tables if not present."""
        if self._conn is None:
            return

        # Check and add to steps table
        cursor = self._conn.execute("PRAGMA table_info(steps)")
        columns = {row[1] for row in cursor.fetchall()}
        if "peak_mem_mb" not in columns:
            self._conn.execute("ALTER TABLE steps ADD COLUMN peak_mem_mb REAL")

        # Check and add to events table
        cursor = self._conn.execute("PRAGMA table_info(events)")
        columns = {row[1] for row in cursor.fetchall()}
        if "peak_mem_mb" not in columns:
            self._conn.execute("ALTER TABLE events ADD COLUMN peak_mem_mb REAL")

        self._conn.commit()

    def register_run(
        self, name: str, step_names: list[str], started_at: float | None = None
    ) -> str:
        """
        Register a new pipeline run with its steps.

        This should be called before the pipeline starts to allow
        the visualizer to show all steps in their pending state.

        Args:
            name: Display name for the run
            step_names: List of step names in execution order
            started_at: Optional start timestamp (defaults to now)

        Returns:
            The run_id for this run
        """
        if self._conn is None:
            return self.run_id

        started_at = started_at or time.time()

        # Insert run
        self._conn.execute(
            """
            INSERT OR REPLACE INTO runs (id, name, started_at, status, total_steps)
            VALUES (?, ?, ?, 'running', ?)
            """,
            (self.run_id, name, started_at, len(step_names)),
        )

        # Insert steps as pending
        for i, step_name in enumerate(step_names):
            self._conn.execute(
                """
                INSERT INTO steps (run_id, name, step_index, status)
                VALUES (?, ?, ?, 'pending')
                """,
                (self.run_id, step_name, i),
            )

        self._conn.commit()
        return self.run_id

    def register_branch(
        self,
        parent_step: str,
        branch_name: str,
        step_names: list[str],
        start_index: int,
    ) -> None:
        """
        Register a branch's steps.

        Args:
            parent_step: Name of the router step that creates this branch
            branch_name: Name of this branch (e.g., "ops", "parts")
            step_names: List of step names in this branch
            start_index: Starting step index for this branch
        """
        if self._conn is None:
            return

        for i, step_name in enumerate(step_names):
            self._conn.execute(
                """
                INSERT INTO steps (run_id, name, step_index, status, branch, parent_step)
                VALUES (?, ?, ?, 'pending', ?, ?)
                """,
                (self.run_id, step_name, start_index + i, branch_name, parent_step),
            )

        self._conn.commit()

    def set_branch_skipped(self, branch_name: str) -> None:
        """Mark all steps in a branch as skipped."""
        if self._conn is None:
            return

        self._conn.execute(
            """
            UPDATE steps SET status = 'skipped'
            WHERE run_id = ? AND branch = ?
            """,
            (self.run_id, branch_name),
        )
        self._conn.commit()

    def complete_run(self, status: str = "completed") -> None:
        """Mark the run as completed."""
        if self._conn is None:
            return

        self._conn.execute(
            """
            UPDATE runs SET completed_at = ?, status = ?
            WHERE id = ?
            """,
            (time.time(), status, self.run_id),
        )
        self._conn.commit()

    def notify(self, event: ProgressEvent) -> None:
        """Store event in SQLite database."""
        if self._conn is None:
            return

        # Insert event
        self._conn.execute(
            """
            INSERT INTO events (
                run_id, timestamp, step_name, step_index, total_steps,
                event_type, duration_s, peak_mem_mb, error, current, total, message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self.run_id,
                event.timestamp,
                event.step_name,
                event.step_index,
                event.total_steps,
                event.event_type,
                event.duration_s,
                event.peak_mem_mb,
                event.error,
                event.current,
                event.total,
                event.message,
            ),
        )

        # Update step status based on event type (use name for lookup to support branches)
        if event.event_type == "started":
            self._conn.execute(
                """
                UPDATE steps SET status = 'running', started_at = ?
                WHERE run_id = ? AND name = ? AND status = 'pending'
                """,
                (event.timestamp, self.run_id, event.step_name),
            )
        elif event.event_type == "completed":
            self._conn.execute(
                """
                UPDATE steps SET status = 'completed', completed_at = ?, duration_s = ?, peak_mem_mb = ?
                WHERE run_id = ? AND name = ? AND status = 'running'
                """,
                (event.timestamp, event.duration_s, event.peak_mem_mb, self.run_id, event.step_name),
            )
        elif event.event_type == "failed":
            self._conn.execute(
                """
                UPDATE steps SET status = 'failed', completed_at = ?, duration_s = ?, error = ?
                WHERE run_id = ? AND name = ? AND status = 'running'
                """,
                (
                    event.timestamp,
                    event.duration_s,
                    event.error,
                    self.run_id,
                    event.step_name,
                ),
            )

        self._conn.commit()

    def get_run(self, run_id: str | None = None) -> dict[str, Any] | None:
        """Get run details by ID."""
        if self._conn is None:
            return None

        run_id = run_id or self.run_id
        cursor = self._conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_steps(
        self, run_id: str | None = None, branch: str | None = None
    ) -> list[dict[str, Any]]:
        """Get all steps for a run, optionally filtered by branch."""
        if self._conn is None:
            return []

        run_id = run_id or self.run_id

        if branch is not None:
            cursor = self._conn.execute(
                "SELECT * FROM steps WHERE run_id = ? AND branch = ? ORDER BY step_index",
                (run_id, branch),
            )
        else:
            # Order: main steps first (branch IS NULL), then branches by parent_step and step_index
            cursor = self._conn.execute(
                """
                SELECT * FROM steps WHERE run_id = ?
                ORDER BY
                    CASE WHEN branch IS NULL THEN 0 ELSE 1 END,
                    step_index,
                    branch
                """,
                (run_id,),
            )
        return [dict(row) for row in cursor.fetchall()]

    def get_branches(self, run_id: str | None = None) -> list[str]:
        """Get all branch names for a run."""
        if self._conn is None:
            return []

        run_id = run_id or self.run_id
        cursor = self._conn.execute(
            "SELECT DISTINCT branch FROM steps WHERE run_id = ? AND branch IS NOT NULL",
            (run_id,),
        )
        return [row[0] for row in cursor.fetchall()]

    def get_events(
        self,
        run_id: str | None = None,
        since_id: int | None = None,
        step_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get events for a run, optionally filtered."""
        if self._conn is None:
            return []

        run_id = run_id or self.run_id
        query = "SELECT * FROM events WHERE run_id = ?"
        params: list[Any] = [run_id]

        if since_id is not None:
            query += " AND id > ?"
            params.append(since_id)

        if step_name is not None:
            query += " AND step_name = ?"
            params.append(step_name)

        query += " ORDER BY id"

        cursor = self._conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_all_runs(self) -> list[dict[str, Any]]:
        """Get all runs, most recent first."""
        if self._conn is None:
            return []

        cursor = self._conn.execute("SELECT * FROM runs ORDER BY started_at DESC")
        return [dict(row) for row in cursor.fetchall()]

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
