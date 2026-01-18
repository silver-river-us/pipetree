"""Controller for pipeline runs."""

from pathlib import Path
from typing import Any

from ..lib.db import get_db_connection


class RunsController:
    """Handles pipeline run requests."""

    @classmethod
    def index(cls, db_path: Path) -> dict[str, Any]:
        """Main dashboard page - shows all runs."""
        runs = []
        if db_path.exists():
            try:
                conn = get_db_connection(db_path)
                cursor = conn.execute(
                    "SELECT * FROM runs ORDER BY started_at DESC LIMIT 50"
                )
                runs = [dict(row) for row in cursor.fetchall()]
                conn.close()
            except Exception:
                pass

        return {
            "template": "index.html",
            "locals": {"runs": runs, "db_path": str(db_path)},
        }

    @classmethod
    def detail(cls, run_id: str, db_path: Path) -> dict[str, Any]:
        """Detail view for a specific run."""
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
            "template": "run_detail.html",
            "locals": {
                "run": run,
                "steps": steps,
                "run_id": run_id,
                "db_path": str(db_path),
            },
        }

    @classmethod
    def list_partial(cls, db_path: Path) -> dict[str, Any]:
        """HTMX partial for runs list."""
        runs = []
        if db_path.exists():
            try:
                conn = get_db_connection(db_path)
                cursor = conn.execute(
                    "SELECT * FROM runs ORDER BY started_at DESC LIMIT 50"
                )
                runs = [dict(row) for row in cursor.fetchall()]
                conn.close()
            except Exception:
                pass

        return {
            "template": "partials/runs_list.html",
            "locals": {"runs": runs, "db_path": str(db_path)},
        }

    @classmethod
    def progress(cls, run_id: str, db_path: Path) -> dict[str, Any]:
        """Get current progress data for a run (JSON for charts)."""
        data: dict[str, Any] = {"run": None, "steps": [], "latest_events": []}

        if db_path.exists():
            try:
                conn = get_db_connection(db_path)

                cursor = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
                row = cursor.fetchone()
                if row:
                    data["run"] = dict(row)

                cursor = conn.execute(
                    "SELECT * FROM steps WHERE run_id = ? ORDER BY step_index",
                    (run_id,),
                )
                steps = [dict(row) for row in cursor.fetchall()]

                for step in steps:
                    if step["status"] == "running":
                        cursor = conn.execute(
                            """
                            SELECT current, total, message FROM events
                            WHERE run_id = ? AND step_index = ? AND event_type = 'progress'
                            ORDER BY id DESC LIMIT 1
                            """,
                            (run_id, step["step_index"]),
                        )
                        progress_row = cursor.fetchone()
                        if progress_row:
                            step["current"] = progress_row["current"]
                            step["total"] = progress_row["total"]
                            step["message"] = progress_row["message"]

                data["steps"] = steps

                conn.close()
            except Exception:
                pass

        return {"json": data}
