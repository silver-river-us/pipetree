import logging

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from visualizer.config import settings

logger = logging.getLogger(__name__)

FROM_EMAIL = "info@silver-river.us"


class MailerError(Exception):
    pass


class Mailer:
    def __init__(self) -> None:
        self._client: SendGridAPIClient | None = None

    def _get_client(self) -> SendGridAPIClient:
        if self._client is None:
            if not settings.sendgrid_api_key:
                raise MailerError("SENDGRID_API_KEY is not configured")
            self._client = SendGridAPIClient(settings.sendgrid_api_key)
        return self._client

    def send(self, to: str, subject: str, body: str) -> bool:
        if settings.log_auth_codes:
            logger.info(f"[MAILER] Email to {to}: {subject}")

        message = Mail(
            from_email=FROM_EMAIL,
            to_emails=to,
            subject=subject,
            plain_text_content=body,
        )

        try:
            client = self._get_client()
            response = client.send(message)
            if response.status_code >= 400:
                raise MailerError(f"SendGrid returned {response.status_code}")
            return True
        except MailerError:
            raise
        except Exception as e:
            raise MailerError(f"Failed to send email: {e}") from e


mailer = Mailer()
