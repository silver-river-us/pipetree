"""Telemetry web controller."""

from pathlib import Path

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse

from lib import telemetry as telemetry_lib

from boundary.base.http_context import get_db_path, get_template_context, require_login
from boundary.base.templates import templates

router = APIRouter()


@router.get("/telemetry", response_class=HTMLResponse)
async def telemetry_index(request: Request, db: str = Query(default=None)):
    """Telemetry dashboard page."""
    if redirect := require_login(request):
        return redirect

    db_path = get_db_path(db, request)
    databases: list[dict] = []
    pipelines = telemetry_lib.get_all_pipelines(db_path, databases)

    return templates().TemplateResponse(
        request,
        "telemetry.html",
        {
            "pipelines": pipelines,
            "db_path": str(db_path),
            **get_template_context(db_path),
        },
    )


@router.get("/telemetry/{run_id}", response_class=HTMLResponse)
async def telemetry_run_detail(request: Request, run_id: str, db: str = Query(...)):
    """Telemetry page for a specific run."""
    if redirect := require_login(request):
        return redirect

    db_path = Path(db)
    data = telemetry_lib.get_run_telemetry(run_id, db_path)

    return templates().TemplateResponse(
        request,
        "run_telemetry.html",
        {
            "run": data["run"],
            "steps": data["steps"],
            "run_id": run_id,
            "db_path": str(db_path),
            "cpu_count": data.get("cpu_count", 1),
            **get_template_context(db_path),
        },
    )


@router.get("/compare", response_class=HTMLResponse)
async def compare_runs(
    request: Request,
    run1: str = Query(...),
    db1: str = Query(...),
    run2: str = Query(...),
    db2: str = Query(...),
):
    """Compare telemetry between two runs."""
    if redirect := require_login(request):
        return redirect

    data = telemetry_lib.compare_runs(run1, Path(db1), run2, Path(db2))

    return templates().TemplateResponse(
        request,
        "compare.html",
        {
            **data,
            **get_template_context(Path(db1)),
        },
    )
