"""Route registration for the visualizer application."""

from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles

from visualizer.boundary import (
    admin_router,
    api_benchmarks_router,
    api_databases_router,
    api_runs_router,
    api_telemetry_router,
    benchmarks_router,
    dashboard_router,
    ingest_router,
    login_router,
    runs_router,
    steps_router,
    telemetry_router,
    websocket_router,
)

ASSETS_DIR = Path(__file__).parent / "boundary" / "assets"


def register_routes(app: FastAPI) -> None:
    """Register all routes on the FastAPI app."""
    # Static files
    app.mount("/static", StaticFiles(directory=ASSETS_DIR / "static"), name="static")

    # Web routes
    app.include_router(admin_router)
    app.include_router(login_router)
    app.include_router(dashboard_router)
    app.include_router(runs_router)
    app.include_router(steps_router)
    app.include_router(telemetry_router)
    app.include_router(benchmarks_router)
    app.include_router(websocket_router)

    # API routes
    api = APIRouter(prefix="/api")
    api.include_router(ingest_router)
    api.include_router(api_runs_router)
    api.include_router(api_telemetry_router)
    api.include_router(api_benchmarks_router)
    api.include_router(api_databases_router)
    app.include_router(api)
