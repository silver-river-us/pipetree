"""Route definitions for the visualizer application."""

import asyncio
import contextlib
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from .controllers import RunsController, StepsController
from .lib.db import get_db_connection

if TYPE_CHECKING:
    from fastapi import FastAPI
    from fastapi.templating import Jinja2Templates


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
        if (
            run_id in self.active_connections
            and websocket in self.active_connections[run_id]
        ):
            self.active_connections[run_id].remove(websocket)

    async def broadcast(self, run_id: str, message: dict):
        if run_id in self.active_connections:
            for connection in self.active_connections[run_id]:
                with contextlib.suppress(Exception):
                    await connection.send_json(message)


manager = ConnectionManager()


def render_controller(request: Request, templates: "Jinja2Templates", response: dict):
    """Render a controller response to an HTML or JSON response."""
    if "json" in response:
        from fastapi.responses import JSONResponse

        return JSONResponse(content=response["json"])

    return templates.TemplateResponse(
        response["template"],
        {"request": request, **response["locals"]},
    )


def register_routes(
    app: "FastAPI", templates: "Jinja2Templates", default_db_path: Path
):
    """Register all routes on the FastAPI app."""

    def get_db_path(db: str | None) -> Path:
        return Path(db) if db else default_db_path

    # --- Dashboard ---

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request, db: str = Query(default=None)):
        """Main dashboard page - shows all runs."""
        response = RunsController.index(get_db_path(db))
        return render_controller(request, templates, response)

    # --- Run detail ---

    @app.get("/runs/{run_id}", response_class=HTMLResponse)
    async def run_detail(request: Request, run_id: str, db: str = Query(default=None)):
        """Detail view for a specific run."""
        response = RunsController.detail(run_id, get_db_path(db))
        return render_controller(request, templates, response)

    # --- HTMX Partials: Steps ---

    @app.get("/runs/{run_id}/steps", response_class=HTMLResponse)
    async def run_steps_partial(
        request: Request, run_id: str, db: str = Query(default=None)
    ):
        """HTMX partial for steps list."""
        response = StepsController.steps_partial(run_id, get_db_path(db))
        return render_controller(request, templates, response)

    @app.get("/runs/{run_id}/steps/data", response_class=HTMLResponse)
    async def run_steps_data_partial(
        request: Request, run_id: str, db: str = Query(default=None)
    ):
        """HTMX partial for steps data."""
        response = StepsController.steps_data_partial(run_id, get_db_path(db))
        return render_controller(request, templates, response)

    @app.get("/runs/{run_id}/steps/list", response_class=HTMLResponse)
    async def run_steps_list_partial(
        request: Request, run_id: str, db: str = Query(default=None)
    ):
        """HTMX partial for step list."""
        response = StepsController.steps_list_partial(run_id, get_db_path(db))
        return render_controller(request, templates, response)

    # --- HTMX Partials: Step Events ---

    @app.get("/runs/{run_id}/step/{step_index}/events", response_class=HTMLResponse)
    async def step_events(
        request: Request,
        run_id: str,
        step_index: int,
        db: str = Query(default=None),
        since_id: int = Query(default=0),
    ):
        """Get events for a specific step (modal content)."""
        response = StepsController.events(run_id, step_index, get_db_path(db), since_id)
        return render_controller(request, templates, response)

    @app.get("/runs/{run_id}/step/{step_index}/summary", response_class=HTMLResponse)
    async def step_summary(
        request: Request,
        run_id: str,
        step_index: int,
        db: str = Query(default=None),
    ):
        """Get a brief summary of the latest step activity."""
        response = StepsController.summary(run_id, step_index, get_db_path(db))
        return render_controller(request, templates, response)

    # --- API Routes ---

    @app.get("/api/runs", response_class=HTMLResponse)
    async def api_runs_list(request: Request, db: str = Query(default=None)):
        """HTMX partial for runs list."""
        response = RunsController.list_partial(get_db_path(db))
        return render_controller(request, templates, response)

    @app.get("/api/runs/{run_id}/progress")
    async def api_run_progress(run_id: str, db: str = Query(default=None)):
        """Get current progress data for a run (JSON)."""
        response = RunsController.progress(run_id, get_db_path(db))
        return response["json"]

    # --- WebSocket ---

    @app.websocket("/ws/{run_id}")
    async def websocket_endpoint(
        websocket: WebSocket, run_id: str, db: str = Query(default=None)
    ):
        """WebSocket endpoint for real-time updates."""
        db_path = get_db_path(db)

        await manager.connect(websocket, run_id)

        last_event_id = 0

        try:
            while True:
                if db_path.exists():
                    try:
                        conn = get_db_connection(db_path)

                        cursor = conn.execute(
                            "SELECT status FROM runs WHERE id = ?", (run_id,)
                        )
                        row = cursor.fetchone()
                        run_status = row["status"] if row else None

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

                            cursor = conn.execute(
                                "SELECT * FROM steps WHERE run_id = ? ORDER BY step_index",
                                (run_id,),
                            )
                            steps = [dict(row) for row in cursor.fetchall()]

                            await websocket.send_json(
                                {
                                    "type": "update",
                                    "run_status": run_status,
                                    "events": events,
                                    "steps": steps,
                                }
                            )

                        conn.close()

                        if run_status in ("completed", "failed"):
                            await websocket.send_json(
                                {"type": "complete", "status": run_status}
                            )
                            break

                    except Exception as e:
                        await websocket.send_json({"type": "error", "message": str(e)})

                await asyncio.sleep(0.1)

        except WebSocketDisconnect:
            manager.disconnect(websocket, run_id)
