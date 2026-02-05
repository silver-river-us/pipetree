from peewee import CharField

from visualizer.infra.db import BaseModel


class Tenant(BaseModel):
    name = CharField(max_length=255)
    slug = CharField(max_length=63, unique=True, index=True)
    api_key = CharField(max_length=64, unique=True, index=True)
    db_name = CharField(max_length=255)

    class Meta:
        table_name = "tenants"
