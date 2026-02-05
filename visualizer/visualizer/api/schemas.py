"""Request/response schemas for the Ingest API."""

from pydantic import BaseModel


class CreateRunRequest(BaseModel):
    id: str
    pipeline: str
    step_names: list[str]
    started_at: float | None = None


class UpdateRunRequest(BaseModel):
    status: str  # "completed" or "failed"


class EventPayload(BaseModel):
    step_name: str
    step_index: int
    total_steps: int
    event_type: str  # "started" | "completed" | "failed" | "progress"
    duration_s: float | None = None
    cpu_time_s: float | None = None
    peak_mem_mb: float | None = None
    error: str | None = None
    current: int | None = None
    total: int | None = None
    message: str | None = None
    timestamp: float | None = None


class BatchEventsRequest(BaseModel):
    events: list[EventPayload]


class RegisterBranchRequest(BaseModel):
    parent_step: str
    branch_name: str
    step_names: list[str]
    start_index: int
