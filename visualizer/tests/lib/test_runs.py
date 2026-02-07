"""Tests for visualizer.lib.runs."""

from pathlib import Path

import pytest

from lib.exceptions import DatabaseNotFoundError, RunNotFoundError
from lib.runs import delete_run, fetch_runs, get_run_detail, get_run_progress


def _corrupt_db(tmp_path: Path) -> Path:
    db_file = tmp_path / "corrupt.db"
    db_file.write_text("not a database")
    return db_file


class TestFetchRuns:
    def test_empty_db(self, pipetree_db: Path) -> None:
        runs, count, names = fetch_runs(pipetree_db)
        assert runs == []
        assert count == 0
        assert names == []

    def test_nonexistent_db(self, tmp_path: Path) -> None:
        runs, count, names = fetch_runs(tmp_path / "nope.db")
        assert runs == []
        assert count == 0

    def test_returns_all_runs(self, seeded_db: Path) -> None:
        runs, count, names = fetch_runs(seeded_db)
        assert count == 2
        assert len(runs) == 2
        assert "pipeline_a" in names
        assert "pipeline_b" in names

    def test_filter_by_status(self, seeded_db: Path) -> None:
        runs, count, _ = fetch_runs(seeded_db, status="completed")
        assert count == 1
        assert runs[0]["status"] == "completed"

    def test_filter_by_pipeline(self, seeded_db: Path) -> None:
        runs, count, _ = fetch_runs(seeded_db, pipeline="pipeline_a")
        assert count == 1
        assert runs[0]["name"] == "pipeline_a"

    def test_pagination(self, seeded_db: Path) -> None:
        runs, count, _ = fetch_runs(seeded_db, page=1, per_page=1)
        assert count == 2
        assert len(runs) == 1

        runs2, _, _ = fetch_runs(seeded_db, page=2, per_page=1)
        assert len(runs2) == 1
        assert runs[0]["id"] != runs2[0]["id"]

    def test_with_databases_list(self, seeded_db: Path) -> None:
        databases = [{"path": str(seeded_db), "name": "test-db"}]
        runs, count, _ = fetch_runs(seeded_db, databases=databases)
        assert count == 2
        assert runs[0]["db_name"] == "test-db"

    def test_databases_with_nonexistent_path(self, seeded_db: Path) -> None:
        databases = [{"path": "/nonexistent/db.db", "name": "bad"}]
        runs, count, _ = fetch_runs(seeded_db, databases=databases)
        assert count == 0

    def test_corrupted_db(self, tmp_path: Path) -> None:
        db = _corrupt_db(tmp_path)
        runs, count, _ = fetch_runs(db)
        assert runs == []
        assert count == 0


class TestGetRunDetail:
    def test_existing_run(self, seeded_db: Path) -> None:
        run, steps = get_run_detail("run-001", seeded_db)
        assert run.id == "run-001"
        assert len(steps) == 3

    def test_nonexistent_run(self, seeded_db: Path) -> None:

        with pytest.raises(RunNotFoundError):
            get_run_detail("no-such-run", seeded_db)

    def test_nonexistent_db(self, tmp_path: Path) -> None:

        with pytest.raises(DatabaseNotFoundError):
            get_run_detail("run-001", tmp_path / "nope.db")

    def test_corrupted_db(self, tmp_path: Path) -> None:
        db = _corrupt_db(tmp_path)

        with pytest.raises(Exception):
            get_run_detail("x", db)


class TestGetRunProgress:
    def test_completed_run(self, seeded_db: Path) -> None:
        data = get_run_progress("run-001", seeded_db)
        assert data["run"] is not None
        assert len(data["steps"]) == 3

    def test_running_step_has_progress(self, seeded_db: Path) -> None:
        data = get_run_progress("run-002", seeded_db)
        assert data["run"] is not None
        running_steps = [s for s in data["steps"] if s["status"] == "running"]
        assert len(running_steps) == 1
        assert running_steps[0]["current"] is not None
        assert running_steps[0]["total"] is not None
        assert running_steps[0]["message"] is not None

    def test_nonexistent_run(self, seeded_db: Path) -> None:

        with pytest.raises(RunNotFoundError):
            get_run_progress("no-run", seeded_db)

    def test_nonexistent_db(self, tmp_path: Path) -> None:

        with pytest.raises(DatabaseNotFoundError):
            get_run_progress("run-001", tmp_path / "nope.db")


class TestDeleteRun:
    def test_delete_existing(self, seeded_db: Path) -> None:
        delete_run("run-001", seeded_db)

        with pytest.raises(RunNotFoundError):
            get_run_detail("run-001", seeded_db)

    def test_delete_nonexistent_db(self, tmp_path: Path) -> None:

        with pytest.raises(DatabaseNotFoundError):
            delete_run("run-001", tmp_path / "nope.db")

    def test_delete_nonexistent_run(self, seeded_db: Path) -> None:
        """Deleting a non-existent run still succeeds (no-op)."""
        delete_run("no-such-run", seeded_db)

    def test_delete_corrupted_db(self, tmp_path: Path) -> None:
        db = _corrupt_db(tmp_path)

        with pytest.raises(Exception):
            delete_run("x", db)
