"""Tests for the visualizer app."""

import pytest
from fastapi.testclient import TestClient

from visualizer.app import app
from visualizer.lib import (
    format_duration,
    format_timestamp,
    get_status_color,
    organize_steps_with_branches,
)


@pytest.fixture
def client() -> TestClient:
    """Create a test client."""
    return TestClient(app)


class TestFormatDuration:
    """Tests for format_duration helper."""

    def test_none(self) -> None:
        assert format_duration(None) == "-"

    def test_milliseconds(self) -> None:
        assert format_duration(0.5) == "500ms"
        assert format_duration(0.001) == "1ms"

    def test_seconds(self) -> None:
        assert format_duration(1.5) == "1.50s"
        assert format_duration(30) == "30.00s"

    def test_minutes(self) -> None:
        assert format_duration(90) == "1m 30.0s"
        assert format_duration(125.5) == "2m 5.5s"


class TestFormatTimestamp:
    """Tests for format_timestamp helper."""

    def test_none(self) -> None:
        assert format_timestamp(None) == "-"

    def test_timestamp(self) -> None:
        # Just check it returns a time-like string
        result = format_timestamp(1700000000.0)
        assert ":" in result


class TestGetStatusColor:
    """Tests for get_status_color helper."""

    def test_known_statuses(self) -> None:
        for status in ["pending", "running", "completed", "failed", "skipped"]:
            colors = get_status_color(status)
            assert "bg" in colors
            assert "text" in colors
            assert "border" in colors

    def test_unknown_status(self) -> None:
        colors = get_status_color("unknown")
        assert colors == get_status_color("pending")


class TestOrganizeStepsWithBranches:
    """Tests for organize_steps_with_branches helper."""

    def test_empty(self) -> None:
        result = organize_steps_with_branches([])
        assert result["main"] == []
        assert result["branches"] == {}

    def test_main_steps_only(self) -> None:
        steps = [
            {"name": "step1", "step_index": 0},
            {"name": "step2", "step_index": 1},
        ]
        result = organize_steps_with_branches(steps)
        assert len(result["main"]) == 2
        assert result["branches"] == {}

    def test_with_branches(self) -> None:
        steps = [
            {"name": "load", "step_index": 0},
            {"name": "route_by_category", "step_index": 1},
            {
                "name": "process_ops",
                "step_index": 2,
                "branch": "ops",
                "parent_step": "route_by_category",
            },
        ]
        result = organize_steps_with_branches(steps)
        assert len(result["main"]) == 2
        assert "ops" in result["branches"]


class TestEndpoints:
    """Tests for API endpoints."""

    def test_index(self, client: TestClient) -> None:
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_runs_list(self, client: TestClient) -> None:
        response = client.get("/api/runs")
        assert response.status_code == 200

    def test_run_detail_not_found(self, client: TestClient) -> None:
        response = client.get("/runs/nonexistent-id")
        assert response.status_code == 200  # Returns page even if run not found

    def test_run_progress_api(self, client: TestClient) -> None:
        response = client.get("/api/runs/test-id/progress")
        assert response.status_code == 200
        data = response.json()
        assert "run" in data
        assert "steps" in data
