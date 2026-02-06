"""Tests for auth context and security tokens."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from boundary.base.http_context import get_current_user
from lib.ctx.auth import authenticate, send_code
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


class TestEncodeToken:
    def test_returns_string(self) -> None:
        token = encode_token("u1", "a@b.com", "t1")
        assert isinstance(token, str)
        assert len(token) > 0


class TestSendCode:
    def test_nonexistent_user(self, peewee_db: Path) -> None:
        result = send_code("nobody@example.com")
        assert result is False

    @patch("lib.ctx.auth.context.mailer")
    def test_existing_user(self, mock_mailer: MagicMock, peewee_db: Path) -> None:
        from lib.ctx.identity.tenant import Tenant
        from lib.ctx.identity.user import User

        tenant = Tenant.create(
            name="Test", slug="test", api_key="key123", db_name="test.db"
        )
        User.create(email="user@example.com", tenant=tenant)

        mock_mailer.send.return_value = True
        result = send_code("user@example.com")
        assert result is True
        mock_mailer.send.assert_called_once()

    @patch("lib.ctx.auth.context.mailer")
    def test_mailer_disabled_prints_code(
        self, mock_mailer: MagicMock, peewee_db: Path
    ) -> None:
        from lib.ctx.identity.tenant import Tenant
        from lib.ctx.identity.user import User

        tenant = Tenant.create(
            name="Test", slug="test", api_key="key123", db_name="test.db"
        )
        User.create(email="user@example.com", tenant=tenant)

        mock_mailer.send.return_value = True
        with patch("lib.ctx.auth.context.settings") as mock_settings:
            mock_settings.mailer_enabled = False
            mock_settings.secret_key = "test"
            result = send_code("user@example.com")
        assert result is True

    @patch("lib.ctx.auth.context.mailer")
    def test_mailer_error_returns_false(
        self, mock_mailer: MagicMock, peewee_db: Path
    ) -> None:
        from infra.mailer import MailerError
        from lib.ctx.identity.tenant import Tenant
        from lib.ctx.identity.user import User

        tenant = Tenant.create(
            name="Test", slug="test", api_key="key123", db_name="test.db"
        )
        User.create(email="user@example.com", tenant=tenant)

        mock_mailer.send.side_effect = MailerError("fail")
        result = send_code("user@example.com")
        assert result is False


class TestAuthenticate:
    def test_invalid_code(self, peewee_db: Path) -> None:
        result = authenticate("user@example.com", "000000")
        assert result is None

    @patch("lib.ctx.auth.context.mailer")
    def test_valid_code(self, mock_mailer: MagicMock, peewee_db: Path) -> None:
        from lib.ctx.identity.tenant import Tenant
        from lib.ctx.identity.user import User

        tenant = Tenant.create(
            name="Test", slug="test", api_key="key123", db_name="test.db"
        )
        User.create(email="user@example.com", tenant=tenant)

        # Send a code first
        mock_mailer.send.return_value = True
        send_code("user@example.com")

        # Retrieve the code from DB
        from lib.ctx.auth.auth_code import AuthCode

        auth_code = AuthCode.get(AuthCode.email == "user@example.com", ~AuthCode.used)

        result = authenticate("user@example.com", auth_code.code)
        assert result is not None
        assert result["email"] == "user@example.com"
        assert result["tenant_name"] == "Test"

    @patch("lib.ctx.auth.context.mailer")
    def test_code_valid_but_user_deleted(
        self, mock_mailer: MagicMock, peewee_db: Path
    ) -> None:
        from lib.ctx.identity.tenant import Tenant
        from lib.ctx.identity.user import User

        tenant = Tenant.create(
            name="Test", slug="test", api_key="key123", db_name="test.db"
        )
        User.create(email="user@example.com", tenant=tenant)

        mock_mailer.send.return_value = True
        send_code("user@example.com")

        from lib.ctx.auth.auth_code import AuthCode

        auth_code = AuthCode.get(AuthCode.email == "user@example.com", ~AuthCode.used)

        # Delete the user before authenticating
        User.delete().execute()

        result = authenticate("user@example.com", auth_code.code)
        assert result is None
