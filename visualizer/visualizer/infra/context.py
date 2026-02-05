import re
import secrets
import uuid

from visualizer.infra.models.tenant import Tenant
from visualizer.infra.models.user import User


def _slugify(name: str) -> str:
    """Convert name to URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug or f"tenant-{uuid.uuid4().hex[:8]}"


def get_tenant(tenant_id: str) -> Tenant | None:
    return Tenant.get_or_none(Tenant.id == tenant_id)


def get_tenant_by_slug(slug: str) -> Tenant | None:
    return Tenant.get_or_none(Tenant.slug == slug)


def get_tenant_by_api_key(api_key: str) -> Tenant | None:
    return Tenant.get_or_none(Tenant.api_key == api_key)


def create_tenant(name: str, db_name: str | None = None) -> Tenant:
    """Create a new tenant with auto-generated slug and API key."""
    slug = _slugify(name)
    base_slug = slug
    while get_tenant_by_slug(slug):
        slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"

    if db_name is None:
        db_name = f"{slug}.db"

    api_key = secrets.token_hex(32)

    return Tenant.create(name=name, slug=slug, api_key=api_key, db_name=db_name)


def list_tenants() -> list[Tenant]:
    return list(Tenant.select().order_by(Tenant.created_at.desc()))


def create_user(email: str, tenant: Tenant) -> User:
    return User.create(email=email.lower().strip(), tenant=tenant)


def get_user_by_email(email: str) -> User | None:
    email = email.lower().strip()
    return User.get_or_none(User.email == email)


def list_users_for_tenant(tenant_id: str) -> list[User]:
    return list(
        User.select().where(User.tenant == tenant_id).order_by(User.created_at.desc())
    )
