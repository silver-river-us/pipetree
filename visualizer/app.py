"""
Pipetree Visualizer - Real-time pipeline monitoring dashboard.

A FastAPI application with WebSocket support for live progress updates.
Styled with Tailwind CSS and Flowbite, uses HTMX for dynamic updates.
"""

import asyncio
import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Configuration
DEFAULT_DB_PATH = Path(__file__).parent.parent / "examples" / "pdf_ingestion" / "progress.db"

app = FastAPI(title="Pipetree Visualizer", version="1.0.0")

# Templates
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

# Static files
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


def get_db_connection(db_path: Path) -> sqlite3.Connection:
    """Get a database connection with row factory."""
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def format_duration(seconds: float | None) -> str:
    """Format duration in human-readable form."""
    if seconds is None:
        return "-"
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    if seconds < 60:
        return f"{seconds:.2f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.1f}s"


def format_timestamp(ts: float | None) -> str:
    """Format timestamp as time string."""
    if ts is None:
        return "-"
    import datetime
    dt = datetime.datetime.fromtimestamp(ts)
    return dt.strftime("%H:%M:%S")


def get_status_color(status: str) -> dict[str, str]:
    """Get Tailwind color classes for a status."""
    colors = {
        "pending": {"bg": "bg-gray-100", "text": "text-gray-600", "border": "border-gray-300", "icon": "clock"},
        "running": {"bg": "bg-blue-100", "text": "text-blue-600", "border": "border-blue-400", "icon": "play"},
        "completed": {"bg": "bg-green-100", "text": "text-green-600", "border": "border-green-400", "icon": "check"},
        "failed": {"bg": "bg-red-100", "text": "text-red-600", "border": "border-red-400", "icon": "x"},
        "skipped": {"bg": "bg-gray-50", "text": "text-gray-400", "border": "border-gray-200", "icon": "skip"},
    }
    return colors.get(status, colors["pending"])


def organize_steps_with_branches(steps: list[dict]) -> dict:
    """Organize steps into main path and nested branch tree."""
    main_steps = []
    # branches maps parent_step -> {branch_name -> [steps]}
    branches_by_parent: dict[str, dict[str, list[dict]]] = {}

    for step in steps:
        branch = step.get("branch")
        parent = step.get("parent_step")
        if branch and parent:
            if parent not in branches_by_parent:
                branches_by_parent[parent] = {}
            if branch not in branches_by_parent[parent]:
                branches_by_parent[parent][branch] = []
            branches_by_parent[parent][branch].append(step)
        else:
            main_steps.append(step)

    # Build tree structure for nested branches
    def build_branch_tree(parent_name: str) -> dict[str, Any]:
        """Recursively build branch tree."""
        if parent_name not in branches_by_parent:
            return {}
        result = {}
        for branch_name, branch_steps in branches_by_parent[parent_name].items():
            result[branch_name] = {
                "steps": branch_steps,
                "children": {},
            }
            # Check if any step in this branch has children
            for step in branch_steps:
                step_name = step.get("name", "")
                if step_name in branches_by_parent:
                    result[branch_name]["children"] = build_branch_tree(step_name)
        return result

    # Find the main router (first one without a parent)
    main_router = None
    for step in main_steps:
        step_name = step.get("name", "")
        if step_name.startswith("route_") and step_name in branches_by_parent:
            main_router = step_name
            break

    branch_tree = build_branch_tree(main_router) if main_router else {}

    # Also provide flat branches for backward compatibility
    flat_branches: dict[str, list[dict]] = {}
    for parent_branches in branches_by_parent.values():
        for branch_name, branch_steps in parent_branches.items():
            if branch_name not in flat_branches:
                flat_branches[branch_name] = []
            flat_branches[branch_name].extend(branch_steps)

    return {
        "main": main_steps,
        "branches": flat_branches,  # Flat for backward compat
        "branch_tree": branch_tree,  # Nested tree structure
        "branches_by_parent": branches_by_parent,  # For detailed control
    }


# Add template filters
templates.env.filters["format_duration"] = format_duration
templates.env.filters["format_timestamp"] = format_timestamp
templates.env.globals["get_status_color"] = get_status_color
templates.env.globals["organize_steps_with_branches"] = organize_steps_with_branches


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: str = Query(default=None)):
    """Main dashboard page - shows all runs."""
    db_path = Path(db) if db else DEFAULT_DB_PATH

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

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "runs": runs, "db_path": str(db_path)},
    )


@app.get("/runs/{run_id}", response_class=HTMLResponse)
async def run_detail(request: Request, run_id: str, db: str = Query(default=None)):
    """Detail view for a specific run."""
    db_path = Path(db) if db else DEFAULT_DB_PATH

    run = None
    steps = []

    if db_path.exists():
        try:
            conn = get_db_connection(db_path)

            # Get run info
            cursor = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
            row = cursor.fetchone()
            if row:
                run = dict(row)

            # Get steps
            cursor = conn.execute(
                "SELECT * FROM steps WHERE run_id = ? ORDER BY step_index",
                (run_id,),
            )
            steps = [dict(row) for row in cursor.fetchall()]

            conn.close()
        except Exception:
            pass

    return templates.TemplateResponse(
        "run_detail.html",
        {
            "request": request,
            "run": run,
            "steps": steps,
            "run_id": run_id,
            "db_path": str(db_path),
        },
    )


@app.get("/runs/{run_id}/steps", response_class=HTMLResponse)
async def run_steps_partial(request: Request, run_id: str, db: str = Query(default=None)):
    """HTMX partial for steps list (for polling updates)."""
    db_path = Path(db) if db else DEFAULT_DB_PATH

    run = None
    steps = []

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

    return templates.TemplateResponse(
        "partials/steps.html",
        {"request": request, "run": run, "steps": steps, "run_id": run_id, "db_path": str(db_path)},
    )


@app.get("/runs/{run_id}/step/{step_index}/events", response_class=HTMLResponse)
async def step_events(
    request: Request,
    run_id: str,
    step_index: int,
    db: str = Query(default=None),
    since_id: int = Query(default=0),
):
    """Get events for a specific step (modal content)."""
    db_path = Path(db) if db else DEFAULT_DB_PATH

    events = []
    step = None
    total_events = 0

    if db_path.exists():
        try:
            conn = get_db_connection(db_path)

            # Get step info
            cursor = conn.execute(
                "SELECT * FROM steps WHERE run_id = ? AND step_index = ?",
                (run_id, step_index),
            )
            row = cursor.fetchone()
            if row:
                step = dict(row)

            # Count total events
            cursor = conn.execute(
                "SELECT COUNT(*) FROM events WHERE run_id = ? AND step_index = ?",
                (run_id, step_index),
            )
            total_events = cursor.fetchone()[0]

            # Get events for this step (only last 50 for initial load, or new ones after since_id)
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
                events.reverse()  # Reverse to show oldest first

            conn.close()
        except Exception:
            pass

    return templates.TemplateResponse(
        "partials/step_events.html",
        {
            "request": request,
            "step": step,
            "events": events,
            "run_id": run_id,
            "db_path": str(db_path),
            "total_events": total_events,
            "since_id": since_id,
        },
    )


@app.get("/runs/{run_id}/step/{step_index}/summary", response_class=HTMLResponse)
async def step_summary(
    request: Request,
    run_id: str,
    step_index: int,
    db: str = Query(default=None),
):
    """Get a brief summary of the latest step activity (for inline display)."""
    db_path = Path(db) if db else DEFAULT_DB_PATH

    latest_event = None
    step = None

    if db_path.exists():
        try:
            conn = get_db_connection(db_path)

            # Get step info
            cursor = conn.execute(
                "SELECT * FROM steps WHERE run_id = ? AND step_index = ?",
                (run_id, step_index),
            )
            row = cursor.fetchone()
            if row:
                step = dict(row)

            # Get the latest event (prefer progress over started)
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

    return templates.TemplateResponse(
        "partials/step_summary.html",
        {"request": request, "step": step, "latest_event": latest_event},
    )


@app.get("/api/runs", response_class=HTMLResponse)
async def api_runs_list(request: Request, db: str = Query(default=None)):
    """HTMX partial for runs list."""
    db_path = Path(db) if db else DEFAULT_DB_PATH

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

    return templates.TemplateResponse(
        "partials/runs_list.html",
        {"request": request, "runs": runs, "db_path": str(db_path)},
    )


@app.get("/api/runs/{run_id}/progress")
async def api_run_progress(run_id: str, db: str = Query(default=None)):
    """Get current progress data for a run (JSON for charts)."""
    db_path = Path(db) if db else DEFAULT_DB_PATH

    data: dict[str, Any] = {"run": None, "steps": [], "latest_events": []}

    if db_path.exists():
        try:
            conn = get_db_connection(db_path)

            # Get run
            cursor = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
            row = cursor.fetchone()
            if row:
                data["run"] = dict(row)

            # Get steps with their latest progress
            cursor = conn.execute(
                "SELECT * FROM steps WHERE run_id = ? ORDER BY step_index",
                (run_id,),
            )
            steps = [dict(row) for row in cursor.fetchall()]

            # Get latest progress event for each running step
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

    return data


class ConnectionManager:
    """Manages WebSocket connections for live updates."""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, run_id: str):
        await websocket.accept()
        if run_id not in self.active_connections:
            self.active_connections[run_id] = []
        self.active_connections[run_id].append(websocket)

    def disconnect(self, websocket: WebSocket, run_id: str):
        if run_id in self.active_connections:
            if websocket in self.active_connections[run_id]:
                self.active_connections[run_id].remove(websocket)

    async def broadcast(self, run_id: str, message: dict):
        if run_id in self.active_connections:
            for connection in self.active_connections[run_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass


manager = ConnectionManager()


@app.websocket("/ws/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str, db: str = Query(default=None)):
    """WebSocket endpoint for real-time updates."""
    db_path = Path(db) if db else DEFAULT_DB_PATH

    await manager.connect(websocket, run_id)

    last_event_id = 0

    try:
        while True:
            # Poll for new events
            if db_path.exists():
                try:
                    conn = get_db_connection(db_path)

                    # Get run status
                    cursor = conn.execute(
                        "SELECT status FROM runs WHERE id = ?", (run_id,)
                    )
                    row = cursor.fetchone()
                    run_status = row["status"] if row else None

                    # Get new events
                    cursor = conn.execute(
                        """
                        SELECT * FROM events
                        WHERE run_id = ? AND id > ?
                        ORDER BY id
                        """,
                        (run_id, last_event_id),
                    )
                    events = [dict(row) for row in cursor.fetchall()]

                    if events:
                        last_event_id = events[-1]["id"]

                        # Get updated steps
                        cursor = conn.execute(
                            "SELECT * FROM steps WHERE run_id = ? ORDER BY step_index",
                            (run_id,),
                        )
                        steps = [dict(row) for row in cursor.fetchall()]

                        await websocket.send_json({
                            "type": "update",
                            "run_status": run_status,
                            "events": events,
                            "steps": steps,
                        })

                    conn.close()

                    # Stop polling if run is completed
                    if run_status in ("completed", "failed"):
                        await websocket.send_json({"type": "complete", "status": run_status})
                        break

                except Exception as e:
                    await websocket.send_json({"type": "error", "message": str(e)})

            # Small delay to prevent tight loop
            await asyncio.sleep(0.1)

    except WebSocketDisconnect:
        manager.disconnect(websocket, run_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
