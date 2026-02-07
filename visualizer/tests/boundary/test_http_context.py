"""Tests for boundary.base.http_context."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from boundary.base.http_context import get_current_user, get_org_context
from lib.security import encode_token


class TestGetCurrentUser:
    def test_no_cookie(self) -> None:
        request = MagicMock()
        request.cookies = {}
        assert get_current_user(request) is None

    def test_invalid_token(self) -> None:
        request = MagicMock()
        request.cookies = {"session": "bad-token"}
        assert get_current_user(request) is None

    def test_valid_token(self) -> None:
        token = encode_token("user-1", "test@example.com", "tenant-1")
        request = MagicMock()
        request.cookies = {"session": token}
        user = get_current_user(request)
        assert user is not None
        assert user["email"] == "test@example.com"
        assert user["tenant_id"] == "tenant-1"


class TestGetOrgContext:
    @pytest.mark.asyncio
    async def test_valid_key(self) -> None:
        mock_creds = MagicMock()
        mock_creds.credentials = "test-key"
        mock_tenant = MagicMock()
        mock_tenant.slug = "org"
        mock_tenant.db_name = "org.db"

        with patch("lib.ctx.identity.context.get_tenant_by_api_key", return_value=mock_tenant):
            with patch("lib.ctx.identity.context.settings") as mock_settings:
                mock_settings.default_db_path = Path("/data")
                slug, db_path = await get_org_context(mock_creds)

        assert slug == "org"
        assert db_path == Path("/data/org.db")

    @pytest.mark.asyncio
    async def test_invalid_key_raises_http_exception(self) -> None:
        mock_creds = MagicMock()
        mock_creds.credentials = "bad-key"

        with patch("lib.ctx.identity.context.get_tenant_by_api_key", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await get_org_context(mock_creds)

            assert exc_info.value.status_code == 401
