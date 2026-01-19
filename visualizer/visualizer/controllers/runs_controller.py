"""Controller for pipetree runs."""

from pathlib import Path
from typing import Any

from pipetree.infrastructure.progress.models import Event, Run, Step, get_session
from sqlmodel import select, delete


class RunsController:
    """Handles pipetree run requests."""

    @classmethod
    def _fetch_runs(
        cls,
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
                    # Get all pipeline names for filter dropdown
                    names_stmt = select(Run.name).distinct().where(Run.name.isnot(None))  # type: ignore[union-attr]
                    names = session.exec(names_stmt).all()
                    pipeline_names.update(n for n in names if n)

                    # Build query with filters
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
                pass

        # Sort all runs by started_at descending
        all_runs.sort(key=lambda r: r.get("started_at") or 0, reverse=True)

        total_count = len(all_runs)

        # Apply pagination
        start = (page - 1) * per_page
        end = start + per_page
        paginated_runs = all_runs[start:end]

        return paginated_runs, total_count, sorted(pipeline_names)

    @classmethod
    def index(
        cls,
        db_path: Path,
        databases: list[dict] | None = None,
        status: str | None = None,
        pipeline: str | None = None,
        page: int = 1,
        per_page: int = 10,
    ) -> dict[str, Any]:
        """Main dashboard page - shows all runs from all databases."""
        runs, total_count, pipeline_names = cls._fetch_runs(
            db_path, databases, status, pipeline, page, per_page
        )

        total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1

        return {
            "template": "index.html",
            "locals": {
                "runs": runs,
                "db_path": str(db_path),
                "total_count": total_count,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
                "pipeline_names": pipeline_names,
                "current_status": status or "",
                "current_pipeline": pipeline or "",
            },
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
        cls,
        db_path: Path,
        databases: list[dict] | None = None,
        status: str | None = None,
        pipeline: str | None = None,
        page: int = 1,
        per_page: int = 10,
    ) -> dict[str, Any]:
        """HTMX partial for runs list from all databases."""
        runs, total_count, pipeline_names = cls._fetch_runs(
            db_path, databases, status, pipeline, page, per_page
        )

        total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1

        return {
            "template": "partials/runs_list.html",
            "locals": {
                "runs": runs,
                "db_path": str(db_path),
                "total_count": total_count,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
                "pipeline_names": pipeline_names,
                "current_status": status or "",
                "current_pipeline": pipeline or "",
            },
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

    @classmethod
    def delete_run(cls, run_id: str, db_path: Path) -> dict[str, Any]:
        """Delete a run and all its associated data."""
        if not db_path.exists():
            return {"json": {"success": False, "error": "Database not found"}}

        try:
            with get_session(db_path) as session:
                # Delete events first (foreign key constraint)
                session.exec(delete(Event).where(Event.run_id == run_id))  # type: ignore[call-overload]
                # Delete steps
                session.exec(delete(Step).where(Step.run_id == run_id))  # type: ignore[call-overload]
                # Delete run
                session.exec(delete(Run).where(Run.id == run_id))  # type: ignore[call-overload]
                session.commit()
            return {"json": {"success": True}}
        except Exception as e:
            return {"json": {"success": False, "error": str(e)}}
