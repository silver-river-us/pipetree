"""Route definitions for the visualizer application."""

import asyncio
import contextlib
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from pipetree.infrastructure.progress.models import Event, Run, Step, get_session
from pydantic import BaseModel
from sqlmodel import select

from .controllers import RunsController, StepsController, TelemetryController

if TYPE_CHECKING:
    from fastapi import FastAPI
    from fastapi.templating import Jinja2Templates


class AddDatabaseRequest(BaseModel):
    name: str
    path: str


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
    from .app import add_database, load_databases, remove_database

    def get_db_path(db: str | None) -> Path:
        """Get database path, preferring config list over env default."""
        if db:
            return Path(db)
        # Use first database from config if available
        databases = load_databases()
        if databases:
            return Path(databases[0]["path"])
        return default_db_path

    def get_template_context(db_path: Path) -> dict:
        """Get common template context including databases list."""
        databases = load_databases()
        return {
            "databases": databases,
            "current_db": str(db_path),
        }

    # --- Database Management API ---

    @app.get("/api/databases")
    async def list_databases():
        """Get list of configured databases."""
        return JSONResponse(content={"databases": load_databases()})

    @app.post("/api/databases")
    async def create_database(data: AddDatabaseRequest):
        """Add a new database to the configuration."""
        db = add_database(data.name, data.path)
        return JSONResponse(content={"database": db})

    @app.delete("/api/databases")
    async def delete_database(path: str = Query(...)):
        """Remove a database from the configuration."""
        success = remove_database(path)
        return JSONResponse(content={"success": success})

    # --- Dashboard ---

    @app.get("/", response_class=HTMLResponse)
    async def index(
        request: Request,
        db: str = Query(default=None),
        status: str = Query(default=None),
        pipeline: str = Query(default=None),
        page: int = Query(default=1, ge=1),
        per_page: int = Query(default=10, ge=1, le=100),
    ):
        """Main dashboard page - shows all runs from all databases."""
        db_path = get_db_path(db)
        databases = load_databases()
        response = RunsController.index(
            db_path, databases, status, pipeline, page, per_page
        )
        response["locals"].update(get_template_context(db_path))
        return render_controller(request, templates, response)

    # --- Run detail ---

    @app.get("/runs/{run_id}", response_class=HTMLResponse)
    async def run_detail(request: Request, run_id: str, db: str = Query(default=None)):
        """Detail view for a specific run."""
        db_path = get_db_path(db)
        response = RunsController.detail(run_id, db_path)
        response["locals"].update(get_template_context(db_path))
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
    async def api_runs_list(
        request: Request,
        db: str = Query(default=None),
        status: str = Query(default=None),
        pipeline: str = Query(default=None),
        page: int = Query(default=1, ge=1),
        per_page: int = Query(default=10, ge=1, le=100),
    ):
        """HTMX partial for runs list from all databases."""
        databases = load_databases()
        response = RunsController.list_partial(
            get_db_path(db), databases, status, pipeline, page, per_page
        )
        return render_controller(request, templates, response)

    @app.get("/api/runs/{run_id}/progress")
    async def api_run_progress(run_id: str, db: str = Query(default=None)):
        """Get current progress data for a run (JSON)."""
        response = RunsController.progress(run_id, get_db_path(db))
        return response["json"]

    # --- Telemetry ---

    @app.get("/telemetry", response_class=HTMLResponse)
    async def telemetry_index(request: Request, db: str = Query(default=None)):
        """Telemetry dashboard page."""
        db_path = get_db_path(db)
        databases = load_databases()
        response = TelemetryController.index(db_path, databases)
        response["locals"].update(get_template_context(db_path))
        return render_controller(request, templates, response)

    @app.get("/api/telemetry/pipelines")
    async def api_telemetry_pipelines(db: str = Query(default=None)):
        """Get list of unique pipeline names with run counts."""
        databases = load_databases()
        response = TelemetryController.get_pipelines(get_db_path(db), databases)
        return JSONResponse(content=response["json"])

    @app.get("/api/telemetry/step-durations")
    async def api_step_durations(
        pipeline: str = Query(...),
        limit: int = Query(default=20),
        db: str = Query(default=None),
    ):
        """Get step duration data for a specific pipeline (for bar/line charts)."""
        databases = load_databases()
        response = TelemetryController.get_step_durations(
            pipeline, limit, get_db_path(db), databases
        )
        return JSONResponse(content=response["json"])

    @app.get("/api/telemetry/run-trends")
    async def api_run_trends(
        pipeline: str = Query(...),
        limit: int = Query(default=20),
        db: str = Query(default=None),
    ):
        """Get run performance trends over time."""
        databases = load_databases()
        response = TelemetryController.get_run_trends(
            pipeline, limit, get_db_path(db), databases
        )
        return JSONResponse(content=response["json"])

    @app.get("/api/telemetry/throughput")
    async def api_throughput(
        pipeline: str = Query(...),
        limit: int = Query(default=20),
        db: str = Query(default=None),
    ):
        """Get throughput metrics (items processed per run)."""
        databases = load_databases()
        response = TelemetryController.get_throughput(
            pipeline, limit, get_db_path(db), databases
        )
        return JSONResponse(content=response["json"])

    # --- Benchmarks (placeholder) ---

    @app.get("/benchmarks", response_class=HTMLResponse)
    async def benchmarks_index(request: Request, db: str = Query(default=None)):
        """Benchmarks page (manual benchmarks - coming soon)."""
        db_path = get_db_path(db)
        return templates.TemplateResponse(
            "benchmarks.html",
            {"request": request, **get_template_context(db_path)},
        )

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
                        with get_session(db_path) as session:
                            # Get run status
                            run_obj = session.get(Run, run_id)
                            run_status = run_obj.status if run_obj else None

                            # Get new events
                            events_stmt = (
                                select(Event)
                                .where(Event.run_id == run_id)
                                .where(Event.id > last_event_id)  # type: ignore[operator]
                                .order_by(Event.id)
                            )
                            event_results = session.exec(events_stmt).all()
                            events = [e.model_dump() for e in event_results]

                            if events:
                                last_event_id = events[-1]["id"]

                                # Get updated steps
                                steps_stmt = (
                                    select(Step)
                                    .where(Step.run_id == run_id)
                                    .order_by(Step.step_index)
                                )
                                step_results = session.exec(steps_stmt).all()
                                steps = [s.model_dump() for s in step_results]

                                await websocket.send_json(
                                    {
                                        "type": "update",
                                        "run_status": run_status,
                                        "events": events,
                                        "steps": steps,
                                    }
                                )

                            if run_status in ("completed", "failed"):
                                await websocket.send_json(
                                    {
                                        "type": "complete",
                                        "status": run_status,
                                        "completed_at": run_obj.completed_at,
                                    }
                                )
                                break

                    except Exception as e:
                        await websocket.send_json({"type": "error", "message": str(e)})

                await asyncio.sleep(0.1)

        except WebSocketDisconnect:
            manager.disconnect(websocket, run_id)
