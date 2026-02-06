"""Tests for lib.ctx.auth.context."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lib.ctx.auth import authenticate, send_code
from lib.exceptions import InvalidCodeError, SendCodeError, UserNotFoundError


class TestSendCode:
    def test_nonexistent_user(self, peewee_db: Path) -> None:
        with pytest.raises(UserNotFoundError):
            send_code("nobody@example.com")

    @patch("lib.ctx.auth.context.mailer")
    def test_existing_user(self, mock_mailer: MagicMock, peewee_db: Path) -> None:
        from lib.ctx.identity.tenant import Tenant
        from lib.ctx.identity.user import User

        tenant = Tenant.create(
            name="Test", slug="test", api_key="key123", db_name="test.db"
        )
        User.create(email="user@example.com", tenant=tenant)

        mock_mailer.send.return_value = True
        send_code("user@example.com")
        mock_mailer.send.assert_called_once()

    @patch("lib.ctx.auth.context.mailer")
    def test_mailer_error(self, mock_mailer: MagicMock, peewee_db: Path) -> None:
        from infra.mailer import MailerError
        from lib.ctx.identity.tenant import Tenant
        from lib.ctx.identity.user import User

        tenant = Tenant.create(
            name="Test", slug="test", api_key="key123", db_name="test.db"
        )
        User.create(email="user@example.com", tenant=tenant)

        mock_mailer.send.side_effect = MailerError("fail")
        with pytest.raises(SendCodeError):
            send_code("user@example.com")


class TestAuthenticate:
    def test_invalid_code(self, peewee_db: Path) -> None:
        with pytest.raises(InvalidCodeError):
            authenticate("user@example.com", "000000")

    @patch("lib.ctx.auth.context.mailer")
    def test_valid_code(self, mock_mailer: MagicMock, peewee_db: Path) -> None:
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

        session = authenticate("user@example.com", auth_code.code)
        assert session.user.email == "user@example.com"
        assert session.tenant.name == "Test"
        assert isinstance(session.token, str)

    @patch("lib.ctx.auth.context.mailer")
    def test_user_deleted_after_code(
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

        User.delete().execute()

        with pytest.raises(UserNotFoundError):
            authenticate("user@example.com", auth_code.code)
