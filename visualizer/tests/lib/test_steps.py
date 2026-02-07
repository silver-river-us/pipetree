"""Tests for visualizer.lib.steps."""

from pathlib import Path

import pytest

from lib.exceptions import DatabaseNotFoundError, RunNotFoundError
from lib.steps import (
    get_step_events,
    get_step_summary,
    get_steps,
)


class TestGetSteps:
    def test_existing_run(self, seeded_db: Path) -> None:
        run, steps = get_steps("run-001", seeded_db)
        assert run.id == "run-001"
        assert len(steps) == 3

    def test_nonexistent_run(self, seeded_db: Path) -> None:
        with pytest.raises(RunNotFoundError):
            get_steps("no-run", seeded_db)

    def test_nonexistent_db(self, tmp_path: Path) -> None:
        with pytest.raises(DatabaseNotFoundError):
            get_steps("run-001", tmp_path / "nope.db")

    def test_corrupted_db(self, tmp_path: Path) -> None:
        db = tmp_path / "corrupt.db"
        db.write_text("not a database")
        with pytest.raises(Exception):
            get_steps("x", db)


class TestGetStepEvents:
    def test_returns_events(self, seeded_db: Path) -> None:
        result = get_step_events("run-002", 1, seeded_db)
        assert result["step"] is not None
        assert result["step"].name == "transform"
        assert len(result["events"]) == 3
        assert result["total_events"] == 3

    def test_with_since_id(self, seeded_db: Path) -> None:
        all_result = get_step_events("run-002", 1, seeded_db)
        first_id = all_result["events"][0].id

        result = get_step_events("run-002", 1, seeded_db, since_id=first_id)
        assert len(result["events"]) == 2

    def test_no_events(self, seeded_db: Path) -> None:
        """Step 0 of run-001 has no events."""
        result = get_step_events("run-001", 0, seeded_db)
        assert result["step"] is not None
        assert result["events"] == []
        assert result["total_events"] == 0

    def test_nonexistent_db(self, tmp_path: Path) -> None:
        with pytest.raises(DatabaseNotFoundError):
            get_step_events("run-001", 0, tmp_path / "nope.db")

    def test_corrupted_db(self, tmp_path: Path) -> None:
        db = tmp_path / "corrupt.db"
        db.write_text("not a database")
        with pytest.raises(Exception):
            get_step_events("x", 0, db)


class TestGetStepSummary:
    def test_step_with_event(self, seeded_db: Path) -> None:
        result = get_step_summary("run-002", 1, seeded_db)
        assert result["step"] is not None
        assert result["latest_event"] is not None
        assert result["latest_event"].event_type == "progress"

    def test_step_without_events(self, seeded_db: Path) -> None:
        result = get_step_summary("run-001", 0, seeded_db)
        assert result["step"] is not None
        assert result["latest_event"] is None

    def test_nonexistent_db(self, tmp_path: Path) -> None:
        with pytest.raises(DatabaseNotFoundError):
            get_step_summary("run-001", 0, tmp_path / "nope.db")

    def test_corrupted_db(self, tmp_path: Path) -> None:
        db = tmp_path / "corrupt.db"
        db.write_text("not a database")
        with pytest.raises(Exception):
            get_step_summary("x", 0, db)
