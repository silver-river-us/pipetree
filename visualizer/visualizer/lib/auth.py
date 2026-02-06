"""Authentication helpers for the boundary layer."""

from fastapi import Request

from visualizer.infra.auth import (
    authenticate as _authenticate,
    decode_token,
    encode_token as _encode_token,
    send_code as _send_code,
)


def get_current_user(request: Request) -> dict | None:
    """Get the current user from the session cookie."""
    token = request.cookies.get("session")
    if not token:
        return None
    return decode_token(token)


def send_code(email: str) -> bool:
    """Send a verification code to the given email."""
    return _send_code(email)


def authenticate(email: str, code: str) -> dict | None:
    """Verify code and return user info dict or None."""
    return _authenticate(email, code)


def encode_token(user_id: str, email: str, tenant_id: str) -> str:
    """Encode user data into a JWT token."""
    return _encode_token(user_id, email, tenant_id)
