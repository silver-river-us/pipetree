import logging
from pathlib import Path

from config import settings
from lib.ctx.identity.tenant import Tenant
from lib.ctx.identity.user import User
from lib.exceptions import InvalidApiKeyError, TenantNotFoundError
from lib.sanitizers import normalize

logger = logging.getLogger(__name__)


def get_tenant(tenant_id: str) -> Tenant | None:
    return Tenant.find_by(id=tenant_id)


def get_tenant_by_slug(slug: str) -> Tenant | None:
    return Tenant.find_by(slug=slug)


def get_tenant_by_api_key(api_key: str) -> Tenant | None:
    return Tenant.find_by(api_key=api_key)


def resolve_org(api_key: str) -> tuple[str, Path]:
    """Resolve an API key to a tenant slug and its pipeline database path."""
    tenant = get_tenant_by_api_key(api_key)

    if tenant is None:
        raise InvalidApiKeyError("Invalid API key")

    db_path = settings.default_db_path / tenant.db_name
    return tenant.slug, db_path


def create_tenant(name: str, db_name: str | None = None) -> Tenant:
    return Tenant.create(name=name, db_name=db_name)


def list_tenants() -> list[Tenant]:
    return list(Tenant.select().order_by(Tenant.created_at.desc()))


def create_user(email: str, tenant: Tenant) -> User:
    email = normalize(email)
    return User.create(email=email, tenant=tenant)


def get_user_by_email(email: str) -> User | None:
    email = normalize(email)
    return User.find_by(email=email)


def list_users_for_tenant(tenant_id: str) -> list[User]:
    return list(
        User.select().where(User.tenant == tenant_id).order_by(User.created_at.desc())
    )


def delete_tenant(tenant_id: str) -> None:
    """Delete a tenant and all associated users."""
    tenant = Tenant.find_by(id=tenant_id)

    if not tenant:
        raise TenantNotFoundError(f"No tenant found for {tenant_id}")

    User.delete().where(User.tenant == tenant_id).execute()
    tenant.delete_instance()

