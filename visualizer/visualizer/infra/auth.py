import logging
import os
from datetime import UTC, datetime, timedelta
from random import randint

import jwt

from visualizer.infra.mailer import MailerError, mailer
from visualizer.infra.models.auth_code import AuthCode
from visualizer.infra.models.user import User

logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
LOG_AUTH_CODES = os.getenv("LOG_AUTH_CODES", "true").lower() in ("true", "1", "yes")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24


def generate_code() -> str:
    return f"{randint(0, 999999):06d}"


def send_code(email: str) -> bool:
    email = email.lower().strip()

    user = User.get_or_none(User.email == email)
    if not user:
        logger.info(f"Login attempt for non-existent user: {email}")
        return False

    code = generate_code()
    expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=10)

    if LOG_AUTH_CODES:
        logger.info(f"Verification code for {email}: {code}")
        print(f"\n{'=' * 50}")
        print(f"  Verification code for {email}: {code}")
        print(f"{'=' * 50}\n")

    try:
        mailer.send(
            to=email,
            subject="Your verification code",
            body=f"Your verification code is: {code}\n\nThis code expires in 10 minutes.",
        )
    except MailerError:
        logger.warning(f"Failed to send code to {email}")
        return False

    # Invalidate existing codes for this email
    AuthCode.update(used=True).where(AuthCode.email == email, ~AuthCode.used).execute()

    AuthCode.create(email=email, code=code, expires_at=expires_at)
    return True


def authenticate(email: str, code: str) -> dict | None:
    """Verify code and return user info dict or None."""
    email = email.lower().strip()

    auth_code = AuthCode.get_or_none(
        AuthCode.email == email,
        AuthCode.code == code,
        ~AuthCode.used,
    )

    if not auth_code or not auth_code.is_valid:
        return None

    auth_code.used = True
    auth_code.save()

    user = User.get_or_none(User.email == email)
    if not user:
        return None

    tenant = user.tenant
    return {
        "user_id": user.id,
        "email": user.email,
        "tenant_id": tenant.id,
        "tenant_name": tenant.name,
    }


def encode_token(user_id: str, email: str, tenant_id: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "tenant_id": tenant_id,
        "exp": datetime.now(UTC).replace(tzinfo=None)
        + timedelta(hours=JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
