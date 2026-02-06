import logging

from infra.mailer import MailerError, mailer
from lib.ctx.auth.auth_code import AuthCode
from lib.ctx.auth.session import Session
from lib.ctx.identity.user import User
from lib.exceptions import InvalidCodeError, SendCodeError, UserNotFoundError
from lib.sanitizers import normalize

logger = logging.getLogger(__name__)


def send_code(email: str) -> None:
    email = normalize(email)

    user = User.get_or_none(User.email == email)
    if not user:
        raise UserNotFoundError(f"No account found for {email}")

    AuthCode.invalidate(email)
    auth_code = AuthCode.create(email=email)

    try:
        mailer.send(
            to=email,
            subject="Your verification code",
            body=f"Your verification code is: {auth_code}\n\nThis code expires in 10 minutes.",
        )
    except MailerError as e:
        raise SendCodeError(f"Failed to send code to {email}") from e


def authenticate(email: str, code: str) -> Session:
    email = normalize(email)

    auth_code = AuthCode.get_or_none(
        AuthCode.email == email,
        AuthCode.code == code,
        ~AuthCode.used,
    )

    if not auth_code or not auth_code.is_valid:
        raise InvalidCodeError("Invalid or expired code")

    auth_code.mark_as_used()

    user = User.get_or_none(User.email == email)
    if not user:
        raise UserNotFoundError(f"No account found for {email}")

    return Session(user=user, tenant=user.tenant)
