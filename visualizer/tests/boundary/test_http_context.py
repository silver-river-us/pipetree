"""Tests for boundary.base.http_context."""

from unittest.mock import MagicMock

from boundary.base.http_context import get_current_user
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
