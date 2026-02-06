import logging
from datetime import UTC, datetime, timedelta
from random import randint

from config import settings
from infra.mailer import MailerError, mailer
from lib.ctx.auth.auth_code import AuthCode
from lib.ctx.identity.user import User

logger = logging.getLogger(__name__)


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

    if not settings.mailer_enabled:
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
