"""Runs API controller."""

from pathlib import Path

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from visualizer.boundary.controllers.web.shared import get_db_path, templates
from visualizer.lib import runs as runs_lib

router = APIRouter()


@router.get("/runs")
async def api_runs_list(
    request: Request,
    db: str = Query(default=None),
    status: str = Query(default=None),
    pipeline: str = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=100),
):
    """HTMX partial for runs list from all databases."""
    databases: list[dict] = []
    db_path = get_db_path(db, request)
    runs, total_count, pipeline_names = runs_lib.fetch_runs(
        db_path, databases, status, pipeline, page, per_page
    )

    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1

    return templates().TemplateResponse(
        "partials/runs_list.html",
        {
            "request": request,
            "runs": runs,
            "db_path": str(db_path),
            "total_count": total_count,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "pipeline_names": pipeline_names,
            "current_status": status or "",
            "current_pipeline": pipeline or "",
        },
    )


@router.get("/runs/{run_id}/progress")
async def api_run_progress(
    request: Request, run_id: str, db: str = Query(default=None)
):
    """Get current progress data for a run (JSON)."""
    db_path = get_db_path(db, request)
    data = runs_lib.get_run_progress(run_id, db_path)
    return data


@router.delete("/runs/{run_id}")
async def api_run_delete(request: Request, run_id: str, db: str = Query(...)):
    """Delete a run and all its associated data."""
    result = runs_lib.delete_run(run_id, Path(db))
    return JSONResponse(content=result)
