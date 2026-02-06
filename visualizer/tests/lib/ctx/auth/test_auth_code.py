"""Tests for lib.ctx.auth.auth_code."""

from datetime import UTC, datetime
from pathlib import Path

from lib.ctx.auth.auth_code import AuthCode


class TestDefaults:
    def test_generates_code(self, peewee_db: Path) -> None:
        auth_code = AuthCode.create(email="test@example.com")
        assert len(auth_code.code) == 6
        assert auth_code.code.isdigit()

    def test_sets_expiration(self, peewee_db: Path) -> None:
        now = datetime.now(UTC).replace(tzinfo=None)
        auth_code = AuthCode.create(email="test@example.com")
        assert auth_code.expires_at > now

    def test_allows_explicit_code(self, peewee_db: Path) -> None:
        auth_code = AuthCode.create(email="test@example.com", code="999999")
        assert auth_code.code == "999999"


class TestStr:
    def test_returns_code(self, peewee_db: Path) -> None:
        auth_code = AuthCode.create(email="test@example.com", code="123456")
        assert str(auth_code) == "123456"
