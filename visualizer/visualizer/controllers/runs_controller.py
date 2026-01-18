"""Controller for pipetree runs."""

from pathlib import Path
from typing import Any

from pipetree.infrastructure.progress.models import Event, Run, Step, get_session
from sqlmodel import select


class RunsController:
    """Handles pipetree run requests."""

    @classmethod
    def index(cls, db_path: Path) -> dict[str, Any]:
        """Main dashboard page - shows all runs."""
        runs: list[dict] = []
        if db_path.exists():
            try:
                with get_session(db_path) as session:
                    statement = (
                        select(Run).order_by(Run.started_at.desc()).limit(50)  # type: ignore[union-attr]
                    )
                    results = session.exec(statement).all()
                    runs = [run.model_dump() for run in results]
            except Exception:
                pass

        return {
            "template": "index.html",
            "locals": {"runs": runs, "db_path": str(db_path)},
        }

    @classmethod
    def detail(cls, run_id: str, db_path: Path) -> dict[str, Any]:
        """Detail view for a specific run."""
        run: dict | None = None
        steps: list[dict] = []

        if db_path.exists():
            try:
                with get_session(db_path) as session:
                    # Get run
                    run_obj = session.get(Run, run_id)
                    if run_obj:
                        run = run_obj.model_dump()

                    # Get steps
                    statement = (
                        select(Step)
                        .where(Step.run_id == run_id)
                        .order_by(Step.step_index)
                    )
                    results = session.exec(statement).all()
                    steps = [step.model_dump() for step in results]
            except Exception:
                pass

        return {
            "template": "run_detail.html",
            "locals": {
                "run": run,
                "steps": steps,
                "run_id": run_id,
                "db_path": str(db_path),
            },
        }

    @classmethod
    def list_partial(cls, db_path: Path) -> dict[str, Any]:
        """HTMX partial for runs list."""
        runs: list[dict] = []
        if db_path.exists():
            try:
                with get_session(db_path) as session:
                    statement = (
                        select(Run).order_by(Run.started_at.desc()).limit(50)  # type: ignore[union-attr]
                    )
                    results = session.exec(statement).all()
                    runs = [run.model_dump() for run in results]
            except Exception:
                pass

        return {
            "template": "partials/runs_list.html",
            "locals": {"runs": runs, "db_path": str(db_path)},
        }

    @classmethod
    def progress(cls, run_id: str, db_path: Path) -> dict[str, Any]:
        """Get current progress data for a run (JSON for charts)."""
        data: dict[str, Any] = {"run": None, "steps": [], "latest_events": []}

        if db_path.exists():
            try:
                with get_session(db_path) as session:
                    # Get run
                    run_obj = session.get(Run, run_id)
                    if run_obj:
                        data["run"] = run_obj.model_dump()

                    # Get steps
                    statement = (
                        select(Step)
                        .where(Step.run_id == run_id)
                        .order_by(Step.step_index)
                    )
                    steps = session.exec(statement).all()
                    step_dicts = []

                    for step in steps:
                        step_dict = step.model_dump()
                        if step.status == "running":
                            # Get latest progress event
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
                pass

        return {"json": data}
