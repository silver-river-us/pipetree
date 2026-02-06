"""Tests for lib.security.tokens."""

from lib.security import decode_token, encode_token


class TestEncodeToken:
    def test_returns_string(self) -> None:
        token = encode_token("u1", "a@b.com", "t1")
        assert isinstance(token, str)
        assert len(token) > 0


class TestDecodeToken:
    def test_valid_token(self) -> None:
        token = encode_token("user-1", "test@example.com", "tenant-1")
        payload = decode_token(token)
        assert payload is not None
        assert payload["email"] == "test@example.com"
        assert payload["tenant_id"] == "tenant-1"

    def test_invalid_token(self) -> None:
        assert decode_token("bad-token") is None
