"""Controller for pipeline steps."""

from pathlib import Path
from typing import Any

from ..lib.db import get_db_connection


class StepsController:
    """Handles pipeline step requests."""

    @classmethod
    def steps_partial(cls, run_id: str, db_path: Path) -> dict[str, Any]:
        """HTMX partial for steps list (for polling updates)."""
        run = None
        steps: list[dict] = []

        if db_path.exists():
            try:
                conn = get_db_connection(db_path)

                cursor = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
                row = cursor.fetchone()
                if row:
                    run = dict(row)

                cursor = conn.execute(
                    "SELECT * FROM steps WHERE run_id = ? ORDER BY step_index",
                    (run_id,),
                )
                steps = [dict(row) for row in cursor.fetchall()]

                conn.close()
            except Exception:
                pass

        return {
            "template": "partials/steps.html",
            "locals": {
                "run": run,
                "steps": steps,
                "run_id": run_id,
                "db_path": str(db_path),
            },
        }

    @classmethod
    def steps_data_partial(cls, run_id: str, db_path: Path) -> dict[str, Any]:
        """HTMX partial for steps data (tree updates)."""
        run = None
        steps: list[dict] = []

        if db_path.exists():
            try:
                conn = get_db_connection(db_path)

                cursor = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
                row = cursor.fetchone()
                if row:
                    run = dict(row)

                cursor = conn.execute(
                    "SELECT * FROM steps WHERE run_id = ? ORDER BY step_index",
                    (run_id,),
                )
                steps = [dict(row) for row in cursor.fetchall()]

                conn.close()
            except Exception:
                pass

        return {
            "template": "partials/steps_data.html",
            "locals": {
                "run": run,
                "steps": steps,
                "run_id": run_id,
                "db_path": str(db_path),
            },
        }

    @classmethod
    def steps_list_partial(cls, run_id: str, db_path: Path) -> dict[str, Any]:
        """HTMX partial for just the step list (lightweight polling)."""
        steps: list[dict] = []

        if db_path.exists():
            try:
                conn = get_db_connection(db_path)

                cursor = conn.execute(
                    "SELECT * FROM steps WHERE run_id = ? ORDER BY step_index",
                    (run_id,),
                )
                steps = [dict(row) for row in cursor.fetchall()]

                conn.close()
            except Exception:
                pass

        return {
            "template": "partials/step_list.html",
            "locals": {"steps": steps, "run_id": run_id, "db_path": str(db_path)},
        }

    @classmethod
    def events(
        cls, run_id: str, step_index: int, db_path: Path, since_id: int = 0
    ) -> dict[str, Any]:
        """Get events for a specific step (modal content)."""
        events: list[dict] = []
        step = None
        total_events = 0

        if db_path.exists():
            try:
                conn = get_db_connection(db_path)

                cursor = conn.execute(
                    "SELECT * FROM steps WHERE run_id = ? AND step_index = ?",
                    (run_id, step_index),
                )
                row = cursor.fetchone()
                if row:
                    step = dict(row)

                cursor = conn.execute(
                    "SELECT COUNT(*) FROM events WHERE run_id = ? AND step_index = ?",
                    (run_id, step_index),
                )
                total_events = cursor.fetchone()[0]

                if since_id > 0:
                    cursor = conn.execute(
                        """
                        SELECT * FROM events
                        WHERE run_id = ? AND step_index = ? AND id > ?
                        ORDER BY id
                        """,
                        (run_id, step_index, since_id),
                    )
                else:
                    cursor = conn.execute(
                        """
                        SELECT * FROM events
                        WHERE run_id = ? AND step_index = ?
                        ORDER BY id DESC LIMIT 50
                        """,
                        (run_id, step_index),
                    )
                events = [dict(row) for row in cursor.fetchall()]
                if since_id == 0:
                    events.reverse()

                conn.close()
            except Exception:
                pass

        return {
            "template": "partials/step_events.html",
            "locals": {
                "step": step,
                "events": events,
                "run_id": run_id,
                "db_path": str(db_path),
                "total_events": total_events,
                "since_id": since_id,
            },
        }

    @classmethod
    def summary(cls, run_id: str, step_index: int, db_path: Path) -> dict[str, Any]:
        """Get a brief summary of the latest step activity."""
        latest_event = None
        step = None

        if db_path.exists():
            try:
                conn = get_db_connection(db_path)

                cursor = conn.execute(
                    "SELECT * FROM steps WHERE run_id = ? AND step_index = ?",
                    (run_id, step_index),
                )
                row = cursor.fetchone()
                if row:
                    step = dict(row)

                cursor = conn.execute(
                    """
                    SELECT * FROM events
                    WHERE run_id = ? AND step_index = ?
                    ORDER BY id DESC LIMIT 1
                    """,
                    (run_id, step_index),
                )
                row = cursor.fetchone()
                if row:
                    latest_event = dict(row)

                conn.close()
            except Exception:
                pass

        return {
            "template": "partials/step_summary.html",
            "locals": {"step": step, "latest_event": latest_event},
        }
