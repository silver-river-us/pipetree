"""Run model - represents a pipeline execution."""

from sqlmodel import Field, Relationship, SQLModel


class Run(SQLModel, table=True):
    """A pipeline run."""

    __tablename__ = "runs"

    id: str = Field(primary_key=True)
    name: str | None = None
    started_at: float | None = None
    completed_at: float | None = None
    status: str = Field(default="pending")
    total_steps: int = Field(default=0)

    # Relationships
    steps: list["Step"] = Relationship(back_populates="run")
    events: list["Event"] = Relationship(back_populates="run")


# Import here to avoid circular imports
from .event import Event  # noqa: E402
from .step import Step  # noqa: E402

Run.model_rebuild()
