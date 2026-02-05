import logging

logger = logging.getLogger(__name__)


class MailerError(Exception):
    pass


class Mailer:
    def send(self, to: str, subject: str, body: str) -> bool:
        logger.info(f"[DEV] Email to {to}: {subject}")
        logger.debug(f"[DEV] Body: {body}")
        return True


mailer = Mailer()
