from peewee import CharField, ForeignKeyField

from infra.db import BaseModel
from lib.ctx.identity.tenant import Tenant


class User(BaseModel):
    email = CharField(max_length=255, unique=True, index=True)
    tenant = ForeignKeyField(Tenant, backref="users", on_delete="CASCADE")

    class Meta:
        table_name = "users"

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower().strip()

        return super().save(*args, **kwargs)
