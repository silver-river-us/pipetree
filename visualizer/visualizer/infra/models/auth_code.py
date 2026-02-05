from datetime import datetime, timezone

from peewee import BooleanField, CharField, DateTimeField

from visualizer.infra.db import BaseModel


class AuthCode(BaseModel):
    email = CharField(max_length=255, index=True)
    code = CharField(max_length=6)
    expires_at = DateTimeField()
    used = BooleanField(default=False)

    class Meta:
        table_name = "auth_codes"

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc).replace(tzinfo=None) > self.expires_at

    @property
    def is_valid(self) -> bool:
        return not self.used and not self.is_expired
