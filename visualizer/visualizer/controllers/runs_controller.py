"""Controller for pipetree runs."""

from pathlib import Path
from typing import Any

from pipetree.infrastructure.progress.models import Event, Run, Step, get_session
from sqlmodel import select


class RunsController:
    """Handles pipetree run requests."""

    @classmethod
    def index(
        cls, db_path: Path, databases: list[dict] | None = None
    ) -> dict[str, Any]:
        """Main dashboard page - shows all runs from all databases."""
        all_runs: list[dict] = []

        # If databases list provided, fetch from all of them
        if databases:
            for db in databases:
                db_file = Path(db["path"])
                if db_file.exists():
                    try:
                        with get_session(db_file) as session:
                            statement = (
                                select(Run).order_by(Run.started_at.desc()).limit(50)  # type: ignore[union-attr]
                            )
                            results = session.exec(statement).all()
                            for run in results:
                                run_dict = run.model_dump()
                                run_dict["db_path"] = str(db_file)
                                run_dict["db_name"] = db["name"]
                                all_runs.append(run_dict)
                    except Exception:
                        pass
        else:
            # Fallback to single database
            if db_path.exists():
                try:
                    with get_session(db_path) as session:
                        statement = (
                            select(Run).order_by(Run.started_at.desc()).limit(50)  # type: ignore[union-attr]
                        )
                        results = session.exec(statement).all()
                        for run in results:
                            run_dict = run.model_dump()
                            run_dict["db_path"] = str(db_path)
                            run_dict["db_name"] = db_path.parent.parent.name
                            all_runs.append(run_dict)
                except Exception:
                    pass

        # Sort all runs by started_at descending
        all_runs.sort(key=lambda r: r.get("started_at") or 0, reverse=True)

        # Limit to 100 most recent
        all_runs = all_runs[:100]

        return {
            "template": "index.html",
            "locals": {"runs": all_runs, "db_path": str(db_path)},
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
    def list_partial(
        cls, db_path: Path, databases: list[dict] | None = None
    ) -> dict[str, Any]:
        """HTMX partial for runs list from all databases."""
        all_runs: list[dict] = []

        # If databases list provided, fetch from all of them
        if databases:
            for db in databases:
                db_file = Path(db["path"])
                if db_file.exists():
                    try:
                        with get_session(db_file) as session:
                            statement = (
                                select(Run).order_by(Run.started_at.desc()).limit(50)  # type: ignore[union-attr]
                            )
                            results = session.exec(statement).all()
                            for run in results:
                                run_dict = run.model_dump()
                                run_dict["db_path"] = str(db_file)
                                run_dict["db_name"] = db["name"]
                                all_runs.append(run_dict)
                    except Exception:
                        pass
        else:
            # Fallback to single database
            if db_path.exists():
                try:
                    with get_session(db_path) as session:
                        statement = (
                            select(Run).order_by(Run.started_at.desc()).limit(50)  # type: ignore[union-attr]
                        )
                        results = session.exec(statement).all()
                        for run in results:
                            run_dict = run.model_dump()
                            run_dict["db_path"] = str(db_path)
                            run_dict["db_name"] = db_path.parent.parent.name
                            all_runs.append(run_dict)
                except Exception:
                    pass

        # Sort all runs by started_at descending
        all_runs.sort(key=lambda r: r.get("started_at") or 0, reverse=True)

        # Limit to 100 most recent
        all_runs = all_runs[:100]

        return {
            "template": "partials/runs_list.html",
            "locals": {"runs": all_runs, "db_path": str(db_path)},
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
