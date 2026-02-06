"""Tests for visualizer.lib.auth."""

from pathlib import Path
from unittest.mock import MagicMock

from visualizer.lib.auth import authenticate, encode_token, get_current_user, send_code


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


class TestEncodeToken:
    def test_returns_string(self) -> None:
        token = encode_token("u1", "a@b.com", "t1")
        assert isinstance(token, str)
        assert len(token) > 0


class TestSendCode:
    def test_nonexistent_user(self, peewee_db: Path) -> None:
        result = send_code("nobody@example.com")
        assert result is False

    def test_existing_user(self, peewee_db: Path) -> None:
        from visualizer.infra.models.tenant import Tenant
        from visualizer.infra.models.user import User

        tenant = Tenant.create(
            name="Test", slug="test", api_key="key123", db_name="test.db"
        )
        User.create(email="user@example.com", tenant=tenant)

        result = send_code("user@example.com")
        assert result is True


class TestAuthenticate:
    def test_invalid_code(self, peewee_db: Path) -> None:
        result = authenticate("user@example.com", "000000")
        assert result is None

    def test_valid_code(self, peewee_db: Path) -> None:
        from visualizer.infra.models.tenant import Tenant
        from visualizer.infra.models.user import User

        tenant = Tenant.create(
            name="Test", slug="test", api_key="key123", db_name="test.db"
        )
        User.create(email="user@example.com", tenant=tenant)

        # Send a code first
        send_code("user@example.com")

        # Retrieve the code from DB
        from visualizer.infra.models.auth_code import AuthCode

        auth_code = AuthCode.get(AuthCode.email == "user@example.com", ~AuthCode.used)

        result = authenticate("user@example.com", auth_code.code)
        assert result is not None
        assert result["email"] == "user@example.com"
        assert result["tenant_name"] == "Test"
