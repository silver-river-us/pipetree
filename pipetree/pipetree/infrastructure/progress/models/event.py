"""Event model - represents a progress event."""

from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .run import Run


class Event(SQLModel, table=True):
    """A progress event from a pipeline step."""

    __tablename__ = "events"

    id: int | None = Field(default=None, primary_key=True)
    run_id: str = Field(foreign_key="runs.id", index=True)
    timestamp: float = Field(index=True)
    step_name: str
    step_index: int
    total_steps: int
    event_type: str
    duration_s: float | None = None
    error: str | None = None
    current: int | None = None
    total: int | None = None
    message: str | None = None
    branch: str | None = None

    # Relationships
    run: "Run" = Relationship(back_populates="events")
