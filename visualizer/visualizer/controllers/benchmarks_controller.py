"""Controller for benchmarks and analytics."""

from pathlib import Path
from typing import Any

from pipetree.infrastructure.progress.models import Event, Run, Step, get_session
from sqlmodel import func, select


class BenchmarksController:
    """Handles benchmark analytics requests."""

    @classmethod
    def index(
        cls, db_path: Path, databases: list[dict] | None = None
    ) -> dict[str, Any]:
        """Benchmarks dashboard page."""
        pipelines = cls._get_all_pipelines(db_path, databases)

        return {
            "template": "benchmarks.html",
            "locals": {
                "pipelines": pipelines,
                "db_path": str(db_path),
            },
        }

    @classmethod
    def get_pipelines(
        cls, db_path: Path, databases: list[dict] | None = None
    ) -> dict[str, Any]:
        """Get list of unique pipeline names with run counts."""
        pipelines = cls._get_all_pipelines(db_path, databases)
        return {"json": {"pipelines": pipelines}}

    @classmethod
    def _get_all_pipelines(
        cls, db_path: Path, databases: list[dict] | None = None
    ) -> list[dict]:
        """Internal: Fetch all unique pipeline names across databases."""
        pipeline_counts: dict[str, dict] = {}

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
                    # Group runs by name (pipeline name)
                    statement = (
                        select(Run.name, func.count(Run.id).label("count"))
                        .where(Run.name.isnot(None))  # type: ignore[union-attr]
                        .group_by(Run.name)
                    )
                    results = session.exec(statement).all()

                    for name, count in results:
                        if name not in pipeline_counts:
                            pipeline_counts[name] = {
                                "name": name,
                                "run_count": 0,
                                "databases": [],
                            }
                        pipeline_counts[name]["run_count"] += count
                        if db_name not in pipeline_counts[name]["databases"]:
                            pipeline_counts[name]["databases"].append(db_name)
            except Exception:
                pass

        # Sort by run count descending
        return sorted(
            pipeline_counts.values(), key=lambda p: p["run_count"], reverse=True
        )

    @classmethod
    def get_step_durations(
        cls,
        pipeline: str,
        limit: int,
        db_path: Path,
        databases: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Get step duration comparison data for charts."""
        runs_data: list[dict] = []

        db_sources: list[Path] = []
        if databases:
            db_sources = [
                Path(db["path"]) for db in databases if Path(db["path"]).exists()
            ]
        elif db_path.exists():
            db_sources = [db_path]

        for db_file in db_sources:
            try:
                with get_session(db_file) as session:
                    # Get recent completed runs for this pipeline
                    runs_stmt = (
                        select(Run)
                        .where(Run.name == pipeline)
                        .where(Run.status == "completed")
                        .order_by(Run.completed_at.desc())  # type: ignore[union-attr]
                        .limit(limit)
                    )
                    runs = session.exec(runs_stmt).all()

                    for run in runs:
                        # Get step durations for this run
                        steps_stmt = (
                            select(Step)
                            .where(Step.run_id == run.id)
                            .order_by(Step.step_index)
                        )
                        steps = session.exec(steps_stmt).all()

                        step_durations = {}
                        for step in steps:
                            if step.duration_s is not None:
                                step_durations[step.name] = step.duration_s

                        runs_data.append(
                            {
                                "run_id": run.id[:8],
                                "started_at": run.started_at,
                                "total_duration": (
                                    run.completed_at - run.started_at
                                    if run.completed_at and run.started_at
                                    else None
                                ),
                                "steps": step_durations,
                            }
                        )
            except Exception:
                pass

        # Sort by started_at and limit
        runs_data.sort(key=lambda r: r.get("started_at") or 0)
        runs_data = runs_data[-limit:]

        # Extract unique step names for chart categories
        step_names: set[str] = set()
        for run in runs_data:
            step_names.update(run["steps"].keys())
        sorted_step_names = sorted(step_names)

        return {
            "json": {
                "runs": runs_data,
                "step_names": sorted_step_names,
                "pipeline": pipeline,
            }
        }

    @classmethod
    def get_run_trends(
        cls,
        pipeline: str,
        limit: int,
        db_path: Path,
        databases: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Get run performance trends over time."""
        trends: list[dict] = []

        db_sources: list[Path] = []
        if databases:
            db_sources = [
                Path(db["path"]) for db in databases if Path(db["path"]).exists()
            ]
        elif db_path.exists():
            db_sources = [db_path]

        for db_file in db_sources:
            try:
                with get_session(db_file) as session:
                    runs_stmt = (
                        select(Run)
                        .where(Run.name == pipeline)
                        .where(Run.status == "completed")
                        .order_by(Run.started_at.desc())  # type: ignore[union-attr]
                        .limit(limit)
                    )
                    runs = session.exec(runs_stmt).all()

                    for run in runs:
                        if run.started_at and run.completed_at:
                            trends.append(
                                {
                                    "run_id": run.id[:8],
                                    "started_at": run.started_at,
                                    "completed_at": run.completed_at,
                                    "duration_s": run.completed_at - run.started_at,
                                    "total_steps": run.total_steps,
                                }
                            )
            except Exception:
                pass

        # Sort by started_at
        trends.sort(key=lambda t: t.get("started_at") or 0)
        trends = trends[-limit:]

        return {"json": {"trends": trends, "pipeline": pipeline}}

    @classmethod
    def get_throughput(
        cls,
        pipeline: str,
        limit: int,
        db_path: Path,
        databases: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Get throughput metrics from progress events."""
        throughput: list[dict] = []

        db_sources: list[Path] = []
        if databases:
            db_sources = [
                Path(db["path"]) for db in databases if Path(db["path"]).exists()
            ]
        elif db_path.exists():
            db_sources = [db_path]

        for db_file in db_sources:
            try:
                with get_session(db_file) as session:
                    runs_stmt = (
                        select(Run)
                        .where(Run.name == pipeline)
                        .where(Run.status == "completed")
                        .order_by(Run.started_at.desc())  # type: ignore[union-attr]
                        .limit(limit)
                    )
                    runs = session.exec(runs_stmt).all()

                    for run in runs:
                        # Get max 'total' from progress events (items processed)
                        events_stmt = (
                            select(func.max(Event.total))
                            .where(Event.run_id == run.id)
                            .where(Event.event_type == "progress")
                            .where(Event.total.isnot(None))  # type: ignore[union-attr]
                        )
                        max_total = session.exec(events_stmt).first()

                        duration = (
                            run.completed_at - run.started_at
                            if run.completed_at and run.started_at
                            else None
                        )

                        throughput.append(
                            {
                                "run_id": run.id[:8],
                                "started_at": run.started_at,
                                "items_processed": max_total or 0,
                                "duration_s": duration,
                                "items_per_second": (
                                    (max_total / duration)
                                    if (max_total and duration and duration > 0)
                                    else None
                                ),
                            }
                        )
            except Exception:
                pass

        # Sort by started_at
        throughput.sort(key=lambda t: t.get("started_at") or 0)
        throughput = throughput[-limit:]

        return {"json": {"throughput": throughput, "pipeline": pipeline}}
