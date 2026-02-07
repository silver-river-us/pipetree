"""Telemetry API controller."""

from pathlib import Path

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from boundary.base.http_context import get_db_path
from lib import telemetry as telemetry_lib

router = APIRouter(prefix="/telemetry")


@router.get("/pipelines")
async def api_telemetry_pipelines(request: Request, db: str = Query(default=None)):
    """Get list of unique pipeline names with run counts."""
    databases: list[dict] = []
    data = telemetry_lib.get_all_pipelines(get_db_path(db, request), databases)
    return JSONResponse(content={"pipelines": data})


@router.get("/step-durations")
async def api_step_durations(
    request: Request,
    pipeline: str = Query(...),
    limit: int = Query(default=20),
    db: str = Query(default=None),
):
    """Get step duration data for a specific pipeline."""
    databases: list[dict] = []

    data = telemetry_lib.get_step_durations(
        pipeline, limit, get_db_path(db, request), databases
    )

    return JSONResponse(content=data)


@router.get("/run-trends")
async def api_run_trends(
    request: Request,
    pipeline: str = Query(...),
    limit: int = Query(default=20),
    db: str = Query(default=None),
):
    """Get run performance trends over time."""
    databases: list[dict] = []

    data = telemetry_lib.get_run_trends(
        pipeline, limit, get_db_path(db, request), databases
    )

    return JSONResponse(content=data)


@router.get("/throughput")
async def api_throughput(
    request: Request,
    pipeline: str = Query(...),
    limit: int = Query(default=20),
    db: str = Query(default=None),
):
    """Get throughput metrics (items processed per run)."""
    databases: list[dict] = []

    data = telemetry_lib.get_throughput(
        pipeline, limit, get_db_path(db, request), databases
    )

    return JSONResponse(content=data)


@router.get("/run/{run_id}")
async def api_telemetry_run(request: Request, run_id: str, db: str = Query(...)):
    """API: Get telemetry data for a specific run."""
    data = telemetry_lib.get_run_telemetry(run_id, Path(db))
    return JSONResponse(content=data)
