"""Business logic for pipetree runs."""

import logging
from pathlib import Path
from typing import Any

from pipetree.infrastructure.progress.models import Event, Run, Step, get_session
from sqlmodel import delete, select

logger = logging.getLogger(__name__)


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
    db_sources: list[tuple[Path, str]] = []

    if databases:
        db_sources = [
            (Path(db["path"]), db["name"])
            for db in databases
            if Path(db["path"]).exists()
        ]
    elif db_path.exists():
        db_sources = [(db_path, db_path.parent.parent.name)]

    for db_file, db_name in db_sources:
        try:
            with get_session(db_file) as session:
                names_stmt = select(Run.name).distinct().where(Run.name.isnot(None))  # type: ignore[union-attr]
                names = session.exec(names_stmt).all()
                pipeline_names.update(n for n in names if n)
                query = select(Run)

                if status:
                    query = query.where(Run.status == status)

                if pipeline:
                    query = query.where(Run.name == pipeline)

                query = query.order_by(Run.started_at.desc())  # type: ignore[union-attr]
                results = session.exec(query).all()

                for run in results:
                    run_dict = run.model_dump()
                    run_dict["db_path"] = str(db_file)
                    run_dict["db_name"] = db_name
                    all_runs.append(run_dict)
        except Exception:
            logger.debug("Failed to query %s", db_file, exc_info=True)

    all_runs.sort(key=lambda r: r.get("started_at") or 0, reverse=True)
    total_count = len(all_runs)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_runs = all_runs[start:end]
    return paginated_runs, total_count, sorted(pipeline_names)


def get_run_detail(run_id: str, db_path: Path) -> tuple[dict | None, list[dict]]:
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
                    select(Step).where(Step.run_id == run_id).order_by(Step.step_index)
                )
                results = session.exec(statement).all()
                steps = [step.model_dump() for step in results]
        except Exception:
            logger.debug("Failed to query %s", db_path, exc_info=True)

    return run, steps


def get_run_progress(run_id: str, db_path: Path) -> dict[str, Any]:
    """Get current progress data for a run."""
    data: dict[str, Any] = {"run": None, "steps": [], "latest_events": []}

    if db_path.exists():
        try:
            with get_session(db_path) as session:
                run_obj = session.get(Run, run_id)

                if run_obj:
                    data["run"] = run_obj.model_dump()

                statement = (
                    select(Step).where(Step.run_id == run_id).order_by(Step.step_index)
                )
                steps = session.exec(statement).all()
                step_dicts = []

                for step in steps:
                    step_dict = step.model_dump()

                    if step.status == "running":
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

                    step_dicts.append(step_dict)

                data["steps"] = step_dicts
        except Exception:
            logger.debug("Failed to query %s", db_path, exc_info=True)

    return data


def delete_run(run_id: str, db_path: Path) -> dict[str, Any]:
    """Delete a run and all its associated data."""

    if not db_path.exists():
        return {"success": False, "error": "Database not found"}

    try:
        with get_session(db_path) as session:
            session.exec(delete(Event).where(Event.run_id == run_id))  # type: ignore[call-overload]
            session.exec(delete(Step).where(Step.run_id == run_id))  # type: ignore[call-overload]
            session.exec(delete(Run).where(Run.id == run_id))  # type: ignore[call-overload]
            session.commit()

        return {"success": True}
    except Exception as e:
        logger.debug("Failed to delete run %s", run_id, exc_info=True)
        return {"success": False, "error": str(e)}
