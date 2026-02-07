"""Business logic for pipetree steps."""

import logging
from pathlib import Path
from typing import Any

from pipetree.infrastructure.progress.models import Event, Run, Step, get_session
from sqlmodel import func, select

from lib.exceptions import DatabaseNotFoundError, RunNotFoundError

logger = logging.getLogger(__name__)


def _require_db(db_path: Path) -> None:
    if not db_path.is_file():
        raise DatabaseNotFoundError(str(db_path))


def _get_run(run_id: str, db_path: Path) -> tuple[Run, list[Step]]:
    """Fetch a run and its steps. Raises if DB or run not found."""
    _require_db(db_path)

    with get_session(db_path) as session:
        run = session.get(Run, run_id)

        if not run:
            raise RunNotFoundError(run_id)

        statement = (
            select(Step).where(Step.run_id == run_id).order_by(Step.step_index)
        )
        steps = list(session.exec(statement).all())

    return run, steps


def get_steps(run_id: str, db_path: Path) -> tuple[Run, list[Step]]:
    """Get run and its steps.

    Raises DatabaseNotFoundError, RunNotFoundError.
    """
    return _get_run(run_id, db_path)


def get_step_events(
    run_id: str, step_index: int, db_path: Path, since_id: int = 0
) -> dict[str, Any]:
    """Get events for a specific step.

    Returns dict with step, events, total_events.
    Raises DatabaseNotFoundError.
    """
    _require_db(db_path)

    with get_session(db_path) as session:
        step = _query_step(session, run_id, step_index)
        total_events = _count_events(session, run_id, step_index)
        events = _query_events(session, run_id, step_index, since_id)

    return {
        "step": step,
        "events": events,
        "total_events": total_events,
    }


def get_step_summary(run_id: str, step_index: int, db_path: Path) -> dict[str, Any]:
    """Get a brief summary of the latest step activity.

    Returns dict with step, latest_event.
    Raises DatabaseNotFoundError.
    """
    _require_db(db_path)

    with get_session(db_path) as session:
        step = _query_step(session, run_id, step_index)
        events_stmt = (
            select(Event)
            .where(Event.run_id == run_id)
            .where(Event.step_index == step_index)
            .order_by(Event.id.desc())  # type: ignore[union-attr]
            .limit(1)
        )
        latest_event = session.exec(events_stmt).first()

    return {"step": step, "latest_event": latest_event}


def _query_step(session: Any, run_id: str, step_index: int) -> Step | None:
    statement = (
        select(Step)
        .where(Step.run_id == run_id)
        .where(Step.step_index == step_index)
    )

    return session.exec(statement).first()


def _count_events(session: Any, run_id: str, step_index: int) -> int:
    count_stmt = (
        select(func.count())
        .select_from(Event)
        .where(Event.run_id == run_id)
        .where(Event.step_index == step_index)
    )

    return session.exec(count_stmt).one()


def _query_events(
    session: Any, run_id: str, step_index: int, since_id: int
) -> list[Event]:
    if since_id > 0:
        events_stmt = (
            select(Event)
            .where(Event.run_id == run_id)
            .where(Event.step_index == step_index)
            .where(Event.id > since_id)  # type: ignore[operator]
            .order_by(Event.id)
        )
        return list(session.exec(events_stmt).all())

    events_stmt = (
        select(Event)
        .where(Event.run_id == run_id)
        .where(Event.step_index == step_index)
        .order_by(Event.id.desc())  # type: ignore[union-attr]
        .limit(50)
    )

    results = list(session.exec(events_stmt).all())
    results.reverse()
    return results
