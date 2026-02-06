"""Runs web controller."""

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse

from lib import runs as runs_lib

from boundary.base.http_context import get_db_path, get_template_context, require_login
from boundary.base.templates import templates

router = APIRouter()


@router.get("/runs/{run_id}", response_class=HTMLResponse)
async def run_detail(request: Request, run_id: str, db: str = Query(default=None)):
    """Detail view for a specific run."""
    if redirect := require_login(request):
        return redirect
    db_path = get_db_path(db, request)
    run, steps = runs_lib.get_run_detail(run_id, db_path)

    return templates().TemplateResponse(
        "run_detail.html",
        {
            "request": request,
            "run": run,
            "steps": steps,
            "run_id": run_id,
            "db_path": str(db_path),
            **get_template_context(db_path),
        },
    )
