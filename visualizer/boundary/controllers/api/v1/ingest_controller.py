"""Ingest API controller for receiving pipeline progress data."""

import time
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pipetree import SQLiteProgressNotifier

from lib.ingest import get_org_context

from .input_objects.ingest import (
    BatchEventsRequest,
    CreateRunRequest,
    RegisterBranchRequest,
    UpdateRunRequest,
)

router = APIRouter(prefix="/v1", tags=["ingest"])


def _get_notifier(db_path: Path, run_id: str) -> SQLiteProgressNotifier:
    """Create a SQLiteProgressNotifier for the given org database and run."""
    return SQLiteProgressNotifier(db_path, run_id=run_id)


@router.post("/runs", status_code=201)
async def create_run(
    data: CreateRunRequest,
    org_ctx: tuple[str, Path] = Depends(get_org_context),
):
    """Register a new pipeline run."""
    org_name, db_path = org_ctx
    notifier = _get_notifier(db_path, data.id)

    try:
        notifier.register_run(
            name=data.pipeline,
            step_names=data.step_names,
            started_at=data.started_at,
        )
    finally:
        notifier.close()

    return JSONResponse(content={"id": data.id, "org": org_name, "status": "running"})


@router.patch("/runs/{run_id}")
async def update_run(
    run_id: str,
    data: UpdateRunRequest,
    org_ctx: tuple[str, Path] = Depends(get_org_context),
):
    """Update run status (complete or fail)."""
    _, db_path = org_ctx
    notifier = _get_notifier(db_path, run_id)

    try:
        notifier.complete_run(status=data.status)
    finally:
        notifier.close()

    return JSONResponse(content={"id": run_id, "status": data.status})


@router.post("/runs/{run_id}/events")
async def push_events(
    run_id: str,
    data: BatchEventsRequest,
    org_ctx: tuple[str, Path] = Depends(get_org_context),
):
    """Push progress events for a run (batch supported)."""
    _, db_path = org_ctx
    notifier = _get_notifier(db_path, run_id)

    try:
        from pipetree import ProgressEvent

        for event in data.events:
            notifier.notify(
                ProgressEvent(
                    timestamp=event.timestamp or time.time(),
                    step_name=event.step_name,
                    step_index=event.step_index,
                    total_steps=event.total_steps,
                    event_type=event.event_type,
                    duration_s=event.duration_s,
                    cpu_time_s=event.cpu_time_s,
                    peak_mem_mb=event.peak_mem_mb,
                    error=event.error,
                    current=event.current,
                    total=event.total,
                    message=event.message,
                )
            )
    finally:
        notifier.close()

    return JSONResponse(content={"run_id": run_id, "events_received": len(data.events)})


@router.post("/runs/{run_id}/branches")
async def register_branch(
    run_id: str,
    data: RegisterBranchRequest,
    org_ctx: tuple[str, Path] = Depends(get_org_context),
):
    """Register a branch for a run."""
    _, db_path = org_ctx
    notifier = _get_notifier(db_path, run_id)

    try:
        notifier.register_branch(
            parent_step=data.parent_step,
            branch_name=data.branch_name,
            step_names=data.step_names,
            start_index=data.start_index,
        )
    finally:
        notifier.close()

    return JSONResponse(
        content={
            "run_id": run_id,
            "branch": data.branch_name,
            "steps": data.step_names,
        }
    )
