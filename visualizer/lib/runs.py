"""Business logic for pipetree runs."""

import logging
from pathlib import Path
from typing import Any

from pipetree.infrastructure.progress.models import Event, Run, Step, get_session
from sqlmodel import delete, select

from lib.exceptions import DatabaseNotFoundError, RunNotFoundError

logger = logging.getLogger(__name__)


def _require_db(db_path: Path) -> None:
    if not db_path.is_file():
        raise DatabaseNotFoundError(str(db_path))


def fetch_runs(
    db_path: Path,
    databases: list[dict] | None = None,
    status: str | None = None,
    pipeline: str | None = None,
    page: int = 1,
    per_page: int = 10,
) -> tuple[list[dict], int, list[str]]:
    """Fetch runs with optional filtering and pagination.

    Returns (runs, total_count, pipeline_names).
    """
    all_runs: list[dict] = []
    pipeline_names: set[str] = set()
    db_sources = _collect_db_sources(db_path, databases)

    for db_file, db_name in db_sources:
        try:
            runs, names = _query_runs_from_db(db_file, db_name, status, pipeline)
            all_runs.extend(runs)
            pipeline_names.update(names)
        except Exception:
            logger.debug("Failed to query %s", db_file, exc_info=True)

    all_runs.sort(key=lambda r: r.get("started_at") or 0, reverse=True)
    total_count = len(all_runs)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_runs = all_runs[start:end]
    return paginated_runs, total_count, sorted(pipeline_names)


def get_run_detail(run_id: str, db_path: Path) -> tuple[Run, list[Step]]:
    """Get run and its steps.

    Raises DatabaseNotFoundError, RunNotFoundError.
    """
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


def get_run_progress(run_id: str, db_path: Path) -> dict[str, Any]:
    """Get current progress data for a run.

    Raises DatabaseNotFoundError.
    """
    _require_db(db_path)

    with get_session(db_path) as session:
        run = session.get(Run, run_id)

        if not run:
            raise RunNotFoundError(run_id)

        statement = (
            select(Step).where(Step.run_id == run_id).order_by(Step.step_index)
        )
        steps = session.exec(statement).all()
        step_dicts = [_enrich_step(session, run_id, step) for step in steps]

    return {"run": run, "steps": step_dicts}


def delete_run(run_id: str, db_path: Path) -> None:
    """Delete a run and all its associated data.

    Raises DatabaseNotFoundError on missing DB.
    """
    _require_db(db_path)

    with get_session(db_path) as session:
        session.exec(delete(Event).where(Event.run_id == run_id))  # type: ignore[call-overload]
        session.exec(delete(Step).where(Step.run_id == run_id))  # type: ignore[call-overload]
        session.exec(delete(Run).where(Run.id == run_id))  # type: ignore[call-overload]
        session.commit()


def _collect_db_sources(
    db_path: Path, databases: list[dict] | None
) -> list[tuple[Path, str]]:
    if databases:
        return [
            (Path(db["path"]), db["name"])
            for db in databases
            if Path(db["path"]).is_file()
        ]

    if db_path.is_file():
        return [(db_path, db_path.parent.parent.name)]

    return []


def _query_runs_from_db(
    db_file: Path, db_name: str, status: str | None, pipeline: str | None
) -> tuple[list[dict], set[str]]:
    with get_session(db_file) as session:
        names_stmt = select(Run.name).distinct().where(Run.name.isnot(None))  # type: ignore[union-attr]
        names = session.exec(names_stmt).all()
        pipeline_names = {n for n in names if n}
        query = select(Run)

        if status:
            query = query.where(Run.status == status)

        if pipeline:
            query = query.where(Run.name == pipeline)

        query = query.order_by(Run.started_at.desc())  # type: ignore[union-attr]
        results = session.exec(query).all()
        runs = []

        for run in results:
            run_dict = run.model_dump()
            run_dict["db_path"] = str(db_file)
            run_dict["db_name"] = db_name
            runs.append(run_dict)

    return runs, pipeline_names


def _enrich_step(session: Any, run_id: str, step: Step) -> dict:
    step_dict = step.model_dump()

    if step.status != "running":
        return step_dict

    progress_stmt = (
        select(Event)
        .where(Event.run_id == run_id)
        .where(Event.step_index == step.step_index)
        .where(Event.event_type == "progress")
        .order_by(Event.id.desc())  # type: ignore[union-attr]
        .limit(1)
    )

    progress_event = session.exec(progress_stmt).first()

    if progress_event:
        step_dict["current"] = progress_event.current
        step_dict["total"] = progress_event.total
        step_dict["message"] = progress_event.message

    return step_dict
