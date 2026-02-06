"""Tests for visualizer.lib.telemetry."""

import time
from pathlib import Path

from pipetree.infrastructure.progress.models import Event, Run, Step
from pipetree.infrastructure.progress.models.database import _engines
from sqlmodel import Session

from lib.telemetry import (
    compare_runs,
    get_all_pipelines,
    get_run_telemetry,
    get_run_trends,
    get_step_durations,
    get_throughput,
)


def _corrupt_db(tmp_path: Path) -> Path:
    db_file = tmp_path / "corrupt.db"
    db_file.write_text("not a database")
    return db_file


def _seed_completed_runs(db_path: Path, count: int = 3) -> None:
    """Seed DB with completed runs for telemetry tests."""
    engine = _engines[str(db_path)]
    now = time.time()

    with Session(engine) as session:
        for i in range(count):
            run = Run(
                id=f"telem-run-{i:03d}",
                name="etl_pipeline",
                started_at=now - (count - i) * 200,
                completed_at=now - (count - i) * 200 + 60,
                status="completed",
                total_steps=2,
            )
            session.add(run)

            for j, step_name in enumerate(["extract", "load"]):
                step = Step(
                    run_id=run.id,
                    name=step_name,
                    step_index=j,
                    status="completed",
                    started_at=run.started_at + j * 25,
                    completed_at=run.started_at + (j + 1) * 25,
                    duration_s=25.0,
                    cpu_time_s=20.0,
                    peak_mem_mb=100.0,
                )
                session.add(step)

            # Progress events
            for k in range(5):
                evt = Event(
                    run_id=run.id,
                    timestamp=run.started_at + k * 10,
                    step_name="extract",
                    step_index=0,
                    total_steps=2,
                    event_type="progress",
                    current=k + 1,
                    total=50,
                    message=f"item {k + 1}",
                )
                session.add(evt)

        session.commit()


class TestGetAllPipelines:
    def test_empty_db(self, pipetree_db: Path) -> None:
        result = get_all_pipelines(pipetree_db)
        assert result == []

    def test_returns_pipeline_counts(self, seeded_db: Path) -> None:
        result = get_all_pipelines(seeded_db)
        assert len(result) == 2
        names = {p["name"] for p in result}
        assert "pipeline_a" in names
        assert "pipeline_b" in names

    def test_nonexistent_db(self, tmp_path: Path) -> None:
        result = get_all_pipelines(tmp_path / "nope.db")
        assert result == []

    def test_with_databases_list(self, seeded_db: Path) -> None:
        databases = [{"path": str(seeded_db), "name": "test"}]
        result = get_all_pipelines(seeded_db, databases=databases)
        assert len(result) == 2

    def test_corrupted_db(self, tmp_path: Path) -> None:
        db = _corrupt_db(tmp_path)
        result = get_all_pipelines(db)
        assert result == []


class TestGetStepDurations:
    def test_returns_step_data(self, pipetree_db: Path) -> None:
        _seed_completed_runs(pipetree_db)
        result = get_step_durations("etl_pipeline", 10, pipetree_db)
        assert result["pipeline"] == "etl_pipeline"
        assert len(result["runs"]) == 3
        assert "extract" in result["step_names"]
        assert "load" in result["step_names"]
        # Steps have duration and memory data
        run = result["runs"][0]
        assert "extract" in run["steps"]
        assert "memory" in run
        assert "cpu_time" in run

    def test_limit(self, pipetree_db: Path) -> None:
        _seed_completed_runs(pipetree_db, count=5)
        result = get_step_durations("etl_pipeline", 2, pipetree_db)
        assert len(result["runs"]) == 2

    def test_nonexistent_pipeline(self, pipetree_db: Path) -> None:
        _seed_completed_runs(pipetree_db)
        result = get_step_durations("no_pipeline", 10, pipetree_db)
        assert result["runs"] == []

    def test_nonexistent_db(self, tmp_path: Path) -> None:
        result = get_step_durations("x", 10, tmp_path / "nope.db")
        assert result["runs"] == []

    def test_with_databases_list(self, pipetree_db: Path) -> None:
        _seed_completed_runs(pipetree_db)
        databases = [{"path": str(pipetree_db), "name": "test"}]
        result = get_step_durations(
            "etl_pipeline", 10, pipetree_db, databases=databases
        )
        assert len(result["runs"]) > 0

    def test_corrupted_db(self, tmp_path: Path) -> None:
        db = _corrupt_db(tmp_path)
        result = get_step_durations("x", 10, db)
        assert result["runs"] == []


class TestGetRunTrends:
    def test_returns_trend_data(self, pipetree_db: Path) -> None:
        _seed_completed_runs(pipetree_db)
        result = get_run_trends("etl_pipeline", 10, pipetree_db)
        assert result["pipeline"] == "etl_pipeline"
        assert len(result["trends"]) == 3
        trend = result["trends"][0]
        assert "duration_s" in trend
        assert "run_id" in trend

    def test_limit(self, pipetree_db: Path) -> None:
        _seed_completed_runs(pipetree_db, count=5)
        result = get_run_trends("etl_pipeline", 2, pipetree_db)
        assert len(result["trends"]) == 2

    def test_nonexistent_db(self, tmp_path: Path) -> None:
        result = get_run_trends("x", 10, tmp_path / "nope.db")
        assert result["trends"] == []

    def test_with_databases_list(self, pipetree_db: Path) -> None:
        _seed_completed_runs(pipetree_db)
        databases = [{"path": str(pipetree_db), "name": "test"}]
        result = get_run_trends("etl_pipeline", 10, pipetree_db, databases=databases)
        assert len(result["trends"]) > 0

    def test_corrupted_db(self, tmp_path: Path) -> None:
        db = _corrupt_db(tmp_path)
        result = get_run_trends("x", 10, db)
        assert result["trends"] == []


class TestGetThroughput:
    def test_returns_throughput_data(self, pipetree_db: Path) -> None:
        _seed_completed_runs(pipetree_db)
        result = get_throughput("etl_pipeline", 10, pipetree_db)
        assert result["pipeline"] == "etl_pipeline"
        assert len(result["throughput"]) == 3
        t = result["throughput"][0]
        assert t["items_processed"] == 50
        assert t["items_per_second"] is not None

    def test_limit(self, pipetree_db: Path) -> None:
        _seed_completed_runs(pipetree_db, count=5)
        result = get_throughput("etl_pipeline", 2, pipetree_db)
        assert len(result["throughput"]) == 2

    def test_nonexistent_db(self, tmp_path: Path) -> None:
        result = get_throughput("x", 10, tmp_path / "nope.db")
        assert result["throughput"] == []

    def test_with_databases_list(self, pipetree_db: Path) -> None:
        _seed_completed_runs(pipetree_db)
        databases = [{"path": str(pipetree_db), "name": "test"}]
        result = get_throughput("etl_pipeline", 10, pipetree_db, databases=databases)
        assert len(result["throughput"]) > 0

    def test_corrupted_db(self, tmp_path: Path) -> None:
        db = _corrupt_db(tmp_path)
        result = get_throughput("x", 10, db)
        assert result["throughput"] == []


class TestGetRunTelemetry:
    def test_returns_run_data(self, pipetree_db: Path) -> None:
        _seed_completed_runs(pipetree_db)
        result = get_run_telemetry("telem-run-000", pipetree_db)
        assert result["run"] is not None
        assert result["run"]["name"] == "etl_pipeline"
        assert result["run"]["duration_s"] is not None
        assert len(result["steps"]) == 2

    def test_nonexistent_run(self, pipetree_db: Path) -> None:
        result = get_run_telemetry("no-run", pipetree_db)
        assert result["run"] is None
        assert result["steps"] == []

    def test_nonexistent_db(self, tmp_path: Path) -> None:
        result = get_run_telemetry("x", tmp_path / "nope.db")
        assert result["run"] is None

    def test_corrupted_db(self, tmp_path: Path) -> None:
        db = _corrupt_db(tmp_path)
        result = get_run_telemetry("x", db)
        assert result["run"] is None


class TestCompareRuns:
    def test_compare_two_runs(self, pipetree_db: Path) -> None:
        _seed_completed_runs(pipetree_db)
        result = compare_runs(
            "telem-run-000", pipetree_db, "telem-run-002", pipetree_db
        )
        assert result["run1"] is not None
        assert result["run2"] is not None
        assert result["run1"]["steps"] is not None
        assert result["run2"]["steps"] is not None
        # run1 should be the earlier one
        assert result["run1"]["started_at"] <= result["run2"]["started_at"]

    def test_chronological_swap(self, pipetree_db: Path) -> None:
        """When run1 is later than run2, they get swapped."""
        _seed_completed_runs(pipetree_db)
        result = compare_runs(
            "telem-run-002", pipetree_db, "telem-run-000", pipetree_db
        )
        # Should auto-sort: run1 = earlier
        assert result["run1"]["started_at"] <= result["run2"]["started_at"]

    def test_nonexistent_run(self, pipetree_db: Path) -> None:
        _seed_completed_runs(pipetree_db)
        result = compare_runs("no-run", pipetree_db, "telem-run-000", pipetree_db)
        assert result["run1"] is None
        assert result["run2"] is not None

    def test_nonexistent_db(self, tmp_path: Path) -> None:
        result = compare_runs("x", tmp_path / "a.db", "y", tmp_path / "b.db")
        assert result["run1"] is None
        assert result["run2"] is None

    def test_corrupted_db(self, tmp_path: Path) -> None:
        db = _corrupt_db(tmp_path)
        result = compare_runs("x", db, "y", db)
        assert result["run1"] is None
        assert result["run2"] is None
