"""Steps web controller (HTMX partials)."""

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse

from lib import steps as steps_lib

from boundary.base.http_context import get_db_path
from boundary.base.templates import templates

router = APIRouter()


@router.get("/runs/{run_id}/steps", response_class=HTMLResponse)
async def run_steps_partial(
    request: Request, run_id: str, db: str = Query(default=None)
):
    """HTMX partial for steps list."""
    db_path = get_db_path(db, request)
    run, steps = steps_lib.get_steps(run_id, db_path)

    return templates().TemplateResponse(
        "partials/steps.html",
        {
            "request": request,
            "run": run,
            "steps": steps,
            "run_id": run_id,
            "db_path": str(db_path),
        },
    )


@router.get("/runs/{run_id}/steps/data", response_class=HTMLResponse)
async def run_steps_data_partial(
    request: Request, run_id: str, db: str = Query(default=None)
):
    """HTMX partial for steps data."""
    db_path = get_db_path(db, request)
    run, steps = steps_lib.get_steps(run_id, db_path)

    return templates().TemplateResponse(
        "partials/steps_data.html",
        {
            "request": request,
            "run": run,
            "steps": steps,
            "run_id": run_id,
            "db_path": str(db_path),
        },
    )


@router.get("/runs/{run_id}/steps/list", response_class=HTMLResponse)
async def run_steps_list_partial(
    request: Request, run_id: str, db: str = Query(default=None)
):
    """HTMX partial for step list."""
    db_path = get_db_path(db, request)
    steps = steps_lib.get_steps_list(run_id, db_path)

    return templates().TemplateResponse(
        "partials/step_list.html",
        {
            "request": request,
            "steps": steps,
            "run_id": run_id,
            "db_path": str(db_path),
        },
    )


@router.get("/runs/{run_id}/step/{step_index}/events", response_class=HTMLResponse)
async def step_events(
    request: Request,
    run_id: str,
    step_index: int,
    db: str = Query(default=None),
    since_id: int = Query(default=0),
):
    """Get events for a specific step (modal content)."""
    db_path = get_db_path(db, request)
    data = steps_lib.get_step_events(run_id, step_index, db_path, since_id)

    return templates().TemplateResponse(
        "partials/step_events.html",
        {
            "request": request,
            "step": data["step"],
            "events": data["events"],
            "run_id": run_id,
            "db_path": str(db_path),
            "total_events": data["total_events"],
            "since_id": since_id,
        },
    )


@router.get("/runs/{run_id}/step/{step_index}/summary", response_class=HTMLResponse)
async def step_summary(
    request: Request,
    run_id: str,
    step_index: int,
    db: str = Query(default=None),
):
    """Get a brief summary of the latest step activity."""
    db_path = get_db_path(db, request)
    data = steps_lib.get_step_summary(run_id, step_index, db_path)

    return templates().TemplateResponse(
        "partials/step_summary.html",
        {
            "request": request,
            "step": data["step"],
            "latest_event": data["latest_event"],
        },
    )
