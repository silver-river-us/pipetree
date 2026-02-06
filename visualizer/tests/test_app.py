"""Tests for the visualizer app."""

import pytest
from fastapi.testclient import TestClient

from app import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client."""
    return TestClient(app)


class TestCreateTables:
    def test_creates_tables(self, peewee_db) -> None:
        from lib import create_tables

        # Tables already exist from peewee_db fixture, just verify no error
        create_tables()


class TestEndpoints:
    """Tests for API endpoints."""

    def test_index_redirects_to_login(self, client: TestClient) -> None:
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/login"

    def test_login_page(self, client: TestClient) -> None:
        response = client.get("/login")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_run_progress_api(self, client: TestClient) -> None:
        response = client.get("/api/runs/test-id/progress")
        assert response.status_code == 200
        data = response.json()
        assert "run" in data
        assert "steps" in data
