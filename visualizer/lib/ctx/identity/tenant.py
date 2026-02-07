import re
import secrets
import uuid

from peewee import CharField

from infra.db import BaseModel


class Tenant(BaseModel):
    name = CharField(max_length=255)
    slug = CharField(max_length=63, unique=True, index=True)
    api_key = CharField(max_length=64, unique=True, index=True)
    db_name = CharField(max_length=255)

    class Meta:
        table_name = "tenants"

    def __init__(self, **kwargs: object) -> None:
        if "slug" not in kwargs and "name" in kwargs:
            kwargs["slug"] = self._unique_slug(str(kwargs["name"]))

        if "api_key" not in kwargs:
            kwargs["api_key"] = secrets.token_hex(32)

        if not kwargs.get("db_name") and "slug" in kwargs:
            kwargs["db_name"] = f"{kwargs['slug']}.db"

        super().__init__(**kwargs)

    @classmethod
    def _slugify(cls, name: str) -> str:
        slug = name.lower().strip()
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        slug = slug.strip("-")
        return slug or f"tenant-{uuid.uuid4().hex[:8]}"

    @classmethod
    def _unique_slug(cls, name: str) -> str:
        slug = cls._slugify(name)
        base_slug = slug

        while cls.find_by(slug=slug):
            slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"

        return slug
