from datetime import UTC, datetime, timedelta
from random import randint

from peewee import BooleanField, CharField, DateTimeField

from infra.db import BaseModel

EXPIRATION_MINUTES = 10


class AuthCode(BaseModel):
    email = CharField(max_length=255, index=True)
    code = CharField(max_length=6)
    expires_at = DateTimeField()
    used = BooleanField(default=False)

    class Meta:
        table_name = "auth_codes"

    def __init__(self, **kwargs: object) -> None:
        if "code" not in kwargs:
            kwargs["code"] = f"{randint(0, 999999):06d}"

        if "expires_at" not in kwargs:
            kwargs["expires_at"] = datetime.now(UTC).replace(tzinfo=None) + timedelta(
                minutes=EXPIRATION_MINUTES
            )

        super().__init__(**kwargs)

    @classmethod
    def invalidate(cls, email: str) -> None:
        cls.update(used=True).where(cls.email == email, ~cls.used).execute()

    def mark_as_used(self) -> None:
        self.used = True
        self.save()

    @property
    def is_expired(self) -> bool:
        return datetime.now(UTC).replace(tzinfo=None) > self.expires_at

    @property
    def is_valid(self) -> bool:
        return not self.used and not self.is_expired

    def __str__(self) -> str:
        return self.code
