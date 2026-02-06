"""Admin business logic for tenant and user management."""

import re
from typing import Any
from uuid import uuid4

from visualizer.infra.models import Tenant, User


def list_tenants() -> list[Any]:
    """List all tenants."""
    return list(Tenant.select())


def get_tenant(tenant_id: str) -> Any | None:
    """Get a tenant by ID."""
    return Tenant.get_or_none(Tenant.id == tenant_id)


def create_tenant(name: str, db_name: str = "") -> Any:
    """Create a new tenant."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    api_key = uuid4().hex + uuid4().hex[:32]
    if not db_name:
        db_name = slug
    return Tenant.create(name=name, slug=slug, api_key=api_key, db_name=db_name)


def delete_tenant(tenant_id: str) -> bool:
    """Delete a tenant and all associated users."""
    tenant = Tenant.get_or_none(Tenant.id == tenant_id)
    if not tenant:
        return False
    User.delete().where(User.tenant == tenant_id).execute()
    tenant.delete_instance()
    return True


def list_users_for_tenant(tenant_id: str) -> list[Any]:
    """List users for a tenant."""
    return list(User.select().where(User.tenant == tenant_id))


def get_user_by_email(email: str) -> Any | None:
    """Get a user by email."""
    return User.get_or_none(User.email == email.lower().strip())


def create_user(email: str, tenant: Any) -> Any:
    """Create a new user for a tenant."""
    return User.create(email=email, tenant=tenant)
