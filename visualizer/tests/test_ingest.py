"""Tests for visualizer.lib.ingest."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from visualizer.lib.ingest import resolve_org, get_org_context


class TestResolveOrg:
    def test_valid_api_key(self) -> None:
        mock_tenant = MagicMock()
        mock_tenant.slug = "acme"
        mock_tenant.db_name = "acme.db"

        with patch("visualizer.lib.ingest.get_tenant_by_api_key", return_value=mock_tenant):
            with patch("visualizer.lib.ingest.settings") as mock_settings:
                mock_settings.default_db_path = Path("/data")
                slug, db_path = resolve_org("valid-key")

        assert slug == "acme"
        assert db_path == Path("/data/acme.db")

    def test_invalid_api_key(self) -> None:
        with patch("visualizer.lib.ingest.get_tenant_by_api_key", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                resolve_org("bad-key")
            assert exc_info.value.status_code == 401


class TestGetOrgContext:
    @pytest.mark.asyncio
    async def test_calls_resolve_org(self) -> None:
        mock_creds = MagicMock()
        mock_creds.credentials = "test-key"

        mock_tenant = MagicMock()
        mock_tenant.slug = "org"
        mock_tenant.db_name = "org.db"

        with patch("visualizer.lib.ingest.get_tenant_by_api_key", return_value=mock_tenant):
            with patch("visualizer.lib.ingest.settings") as mock_settings:
                mock_settings.default_db_path = Path("/data")
                slug, db_path = await get_org_context(mock_creds)

        assert slug == "org"
        assert db_path == Path("/data/org.db")
