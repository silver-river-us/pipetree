"""Step model - represents a pipeline step."""

from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .run import Run


class Step(SQLModel, table=True):
    """A step in a pipeline run."""

    __tablename__ = "steps"

    id: int | None = Field(default=None, primary_key=True)
    run_id: str = Field(foreign_key="runs.id", index=True)
    name: str
    step_index: int
    status: str = Field(default="pending")
    started_at: float | None = None
    completed_at: float | None = None
    duration_s: float | None = None
    error: str | None = None
    branch: str | None = Field(default=None, index=True)
    parent_step: str | None = None

    # Relationships
    run: "Run" = Relationship(back_populates="steps")
