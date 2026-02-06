"""Dashboard web controller."""

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse

from visualizer.lib import runs as runs_lib

from .shared import get_db_path, get_template_context, require_login, templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    db: str = Query(default=None),
    status: str = Query(default=None),
    pipeline: str = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=100),
):
    """Main dashboard page - shows all runs from all databases."""
    if redirect := require_login(request):
        return redirect
    db_path = get_db_path(db, request)
    databases: list[dict] = []
    runs, total_count, pipeline_names = runs_lib.fetch_runs(
        db_path, databases, status, pipeline, page, per_page
    )

    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1

    return templates().TemplateResponse(
        "index.html",
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
            **get_template_context(db_path),
        },
    )
