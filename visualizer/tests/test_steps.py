"""Tests for visualizer.lib.steps."""

from pathlib import Path

from visualizer.lib.steps import (
    get_step_events,
    get_step_summary,
    get_steps,
    get_steps_list,
)


def _corrupt_db(tmp_path: Path) -> Path:
    db_file = tmp_path / "corrupt.db"
    db_file.write_text("not a database")
    return db_file


class TestGetSteps:
    def test_existing_run(self, seeded_db: Path) -> None:
        run, steps = get_steps("run-001", seeded_db)
        assert run is not None
        assert run["id"] == "run-001"
        assert len(steps) == 3

    def test_nonexistent_run(self, seeded_db: Path) -> None:
        run, steps = get_steps("no-run", seeded_db)
        assert run is None
        assert steps == []

    def test_nonexistent_db(self, tmp_path: Path) -> None:
        run, steps = get_steps("run-001", tmp_path / "nope.db")
        assert run is None
        assert steps == []

    def test_corrupted_db(self, tmp_path: Path) -> None:
        db = _corrupt_db(tmp_path)
        run, steps = get_steps("x", db)
        assert run is None
        assert steps == []


class TestGetStepsList:
    def test_returns_steps(self, seeded_db: Path) -> None:
        steps = get_steps_list("run-001", seeded_db)
        assert len(steps) == 3
        assert steps[0]["name"] == "load"

    def test_empty_for_nonexistent_run(self, seeded_db: Path) -> None:
        steps = get_steps_list("no-run", seeded_db)
        assert steps == []

    def test_nonexistent_db(self, tmp_path: Path) -> None:
        steps = get_steps_list("run-001", tmp_path / "nope.db")
        assert steps == []

    def test_corrupted_db(self, tmp_path: Path) -> None:
        db = _corrupt_db(tmp_path)
        steps = get_steps_list("x", db)
        assert steps == []


class TestGetStepEvents:
    def test_returns_events(self, seeded_db: Path) -> None:
        result = get_step_events("run-002", 1, seeded_db)
        assert result["step"] is not None
        assert result["step"]["name"] == "transform"
        assert len(result["events"]) == 3
        assert result["total_events"] == 3

    def test_with_since_id(self, seeded_db: Path) -> None:
        # First get all events to find IDs
        all_result = get_step_events("run-002", 1, seeded_db)
        first_id = all_result["events"][0]["id"]

        result = get_step_events("run-002", 1, seeded_db, since_id=first_id)
        # Should return events after the first one
        assert len(result["events"]) == 2

    def test_no_events(self, seeded_db: Path) -> None:
        """Step 0 of run-001 has no events."""
        result = get_step_events("run-001", 0, seeded_db)
        assert result["step"] is not None
        assert result["events"] == []
        assert result["total_events"] == 0

    def test_nonexistent_db(self, tmp_path: Path) -> None:
        result = get_step_events("run-001", 0, tmp_path / "nope.db")
        assert result["step"] is None
        assert result["events"] == []

    def test_corrupted_db(self, tmp_path: Path) -> None:
        db = _corrupt_db(tmp_path)
        result = get_step_events("x", 0, db)
        assert result["step"] is None
        assert result["events"] == []


class TestGetStepSummary:
    def test_step_with_event(self, seeded_db: Path) -> None:
        result = get_step_summary("run-002", 1, seeded_db)
        assert result["step"] is not None
        assert result["latest_event"] is not None
        assert result["latest_event"]["event_type"] == "progress"

    def test_step_without_events(self, seeded_db: Path) -> None:
        result = get_step_summary("run-001", 0, seeded_db)
        assert result["step"] is not None
        assert result["latest_event"] is None

    def test_nonexistent_db(self, tmp_path: Path) -> None:
        result = get_step_summary("run-001", 0, tmp_path / "nope.db")
        assert result["step"] is None
        assert result["latest_event"] is None

    def test_corrupted_db(self, tmp_path: Path) -> None:
        db = _corrupt_db(tmp_path)
        result = get_step_summary("x", 0, db)
        assert result["step"] is None
        assert result["latest_event"] is None
