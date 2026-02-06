"""Business logic for pipetree steps."""

from pathlib import Path
from typing import Any

from pipetree.infrastructure.progress.models import Event, Run, Step, get_session
from sqlmodel import func, select


def get_steps(
    run_id: str, db_path: Path
) -> tuple[dict | None, list[dict]]:
    """Get run and its steps.

    Returns (run, steps).
    """
    run: dict | None = None
    steps: list[dict] = []

    if db_path.exists():
        try:
            with get_session(db_path) as session:
                run_obj = session.get(Run, run_id)
                if run_obj:
                    run = run_obj.model_dump()

                statement = (
                    select(Step)
                    .where(Step.run_id == run_id)
                    .order_by(Step.step_index)
                )
                results = session.exec(statement).all()
                steps = [step.model_dump() for step in results]
        except Exception:
            pass

    return run, steps


def get_steps_list(run_id: str, db_path: Path) -> list[dict]:
    """Get just the step list (lightweight)."""
    steps: list[dict] = []

    if db_path.exists():
        try:
            with get_session(db_path) as session:
                statement = (
                    select(Step)
                    .where(Step.run_id == run_id)
                    .order_by(Step.step_index)
                )
                results = session.exec(statement).all()
                steps = [step.model_dump() for step in results]
        except Exception:
            pass

    return steps


def get_step_events(
    run_id: str, step_index: int, db_path: Path, since_id: int = 0
) -> dict[str, Any]:
    """Get events for a specific step.

    Returns dict with step, events, total_events.
    """
    events: list[dict] = []
    step: dict | None = None
    total_events = 0

    if db_path.exists():
        try:
            with get_session(db_path) as session:
                statement = (
                    select(Step)
                    .where(Step.run_id == run_id)
                    .where(Step.step_index == step_index)
                )
                step_obj = session.exec(statement).first()
                if step_obj:
                    step = step_obj.model_dump()

                count_stmt = (
                    select(func.count())
                    .select_from(Event)
                    .where(Event.run_id == run_id)
                    .where(Event.step_index == step_index)
                )
                total_events = session.exec(count_stmt).one()

                if since_id > 0:
                    events_stmt = (
                        select(Event)
                        .where(Event.run_id == run_id)
                        .where(Event.step_index == step_index)
                        .where(Event.id > since_id)  # type: ignore[operator]
                        .order_by(Event.id)
                    )
                else:
                    events_stmt = (
                        select(Event)
                        .where(Event.run_id == run_id)
                        .where(Event.step_index == step_index)
                        .order_by(Event.id.desc())  # type: ignore[union-attr]
                        .limit(50)
                    )

                results = session.exec(events_stmt).all()
                events = [event.model_dump() for event in results]
                if since_id == 0:
                    events.reverse()
        except Exception:
            pass

    return {
        "step": step,
        "events": events,
        "total_events": total_events,
    }


def get_step_summary(
    run_id: str, step_index: int, db_path: Path
) -> dict[str, Any]:
    """Get a brief summary of the latest step activity.

    Returns dict with step, latest_event.
    """
    latest_event: dict | None = None
    step: dict | None = None

    if db_path.exists():
        try:
            with get_session(db_path) as session:
                statement = (
                    select(Step)
                    .where(Step.run_id == run_id)
                    .where(Step.step_index == step_index)
                )
                step_obj = session.exec(statement).first()
                if step_obj:
                    step = step_obj.model_dump()

                events_stmt = (
                    select(Event)
                    .where(Event.run_id == run_id)
                    .where(Event.step_index == step_index)
                    .order_by(Event.id.desc())  # type: ignore[union-attr]
                    .limit(1)
                )
                event_obj = session.exec(events_stmt).first()
                if event_obj:
                    latest_event = event_obj.model_dump()
        except Exception:
            pass

    return {"step": step, "latest_event": latest_event}
