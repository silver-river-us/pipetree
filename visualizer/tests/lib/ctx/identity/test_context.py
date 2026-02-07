"""Tests for lib.ctx.identity.context."""

from pathlib import Path

import pytest

from unittest.mock import MagicMock, patch

from lib.ctx.identity import (
    create_tenant,
    create_user,
    delete_tenant,
    get_tenant,
    get_tenant_by_api_key,
    get_tenant_by_slug,
    get_user_by_email,
    list_tenants,
    list_users_for_tenant,
    resolve_org,
)
from lib.exceptions import InvalidApiKeyError, TenantNotFoundError


class TestListTenants:
    def test_empty(self, peewee_db: Path) -> None:
        assert list_tenants() == []

    def test_returns_tenants(self, peewee_db: Path) -> None:
        create_tenant("Acme Corp")
        result = list_tenants()
        assert len(result) == 1


class TestGetTenant:
    def test_nonexistent(self, peewee_db: Path) -> None:
        assert get_tenant("no-such-id") is None

    def test_existing(self, peewee_db: Path) -> None:
        tenant = create_tenant("Acme Corp")
        result = get_tenant(tenant.id)
        assert result is not None
        assert result.name == "Acme Corp"


class TestGetTenantBySlug:
    def test_nonexistent(self, peewee_db: Path) -> None:
        assert get_tenant_by_slug("no-such-slug") is None

    def test_existing(self, peewee_db: Path) -> None:
        tenant = create_tenant("Acme Corp")
        result = get_tenant_by_slug(tenant.slug)
        assert result is not None
        assert result.id == tenant.id


class TestCreateTenant:
    def test_auto_slug_and_api_key(self, peewee_db: Path) -> None:
        tenant = create_tenant("My Org")
        assert tenant.slug == "my-org"
        assert len(tenant.api_key) > 0
        assert tenant.db_name == "my-org.db"

    def test_custom_db_name(self, peewee_db: Path) -> None:
        tenant = create_tenant("Test Org", db_name="custom.db")
        assert tenant.db_name == "custom.db"

    def test_slug_collision(self, peewee_db: Path) -> None:
        t1 = create_tenant("Dup Name")
        t2 = create_tenant("Dup Name")
        assert t1.slug != t2.slug
        assert t2.slug.startswith("dup-name-")


class TestDeleteTenant:
    def test_existing(self, peewee_db: Path) -> None:
        tenant = create_tenant("To Delete")
        delete_tenant(tenant.id)
        assert get_tenant(tenant.id) is None

    def test_nonexistent(self, peewee_db: Path) -> None:
        with pytest.raises(TenantNotFoundError):
            delete_tenant("no-such-id")

    def test_cascades_users(self, peewee_db: Path) -> None:
        tenant = create_tenant("With Users")
        create_user("a@b.com", tenant)
        delete_tenant(tenant.id)
        assert list_users_for_tenant(tenant.id) == []


class TestListUsersForTenant:
    def test_empty(self, peewee_db: Path) -> None:
        tenant = create_tenant("Empty Org")
        assert list_users_for_tenant(tenant.id) == []

    def test_returns_users(self, peewee_db: Path) -> None:
        tenant = create_tenant("Org")
        create_user("a@b.com", tenant)
        result = list_users_for_tenant(tenant.id)
        assert len(result) == 1


class TestGetUserByEmail:
    def test_nonexistent(self, peewee_db: Path) -> None:
        assert get_user_by_email("nobody@x.com") is None

    def test_existing(self, peewee_db: Path) -> None:
        tenant = create_tenant("Org")
        create_user("test@example.com", tenant)
        user = get_user_by_email("test@example.com")
        assert user is not None
        assert user.email == "test@example.com"

    def test_case_insensitive(self, peewee_db: Path) -> None:
        tenant = create_tenant("Org")
        create_user("Test@Example.COM", tenant)
        user = get_user_by_email("  test@example.com  ")
        assert user is not None


class TestGetTenantByApiKey:
    def test_nonexistent(self, peewee_db: Path) -> None:
        assert get_tenant_by_api_key("no-such-key") is None

    def test_existing(self, peewee_db: Path) -> None:
        tenant = create_tenant("Org")
        result = get_tenant_by_api_key(tenant.api_key)
        assert result is not None
        assert result.id == tenant.id


class TestResolveOrg:
    def test_valid_api_key(self) -> None:
        mock_tenant = MagicMock()
        mock_tenant.slug = "acme"
        mock_tenant.db_name = "acme.db"

        with patch("lib.ctx.identity.context.get_tenant_by_api_key", return_value=mock_tenant):
            with patch("lib.ctx.identity.context.settings") as mock_settings:
                mock_settings.default_db_path = Path("/data")
                slug, db_path = resolve_org("valid-key")

        assert slug == "acme"
        assert db_path == Path("/data/acme.db")

    def test_invalid_api_key(self) -> None:
        with patch("lib.ctx.identity.context.get_tenant_by_api_key", return_value=None):
            with pytest.raises(InvalidApiKeyError):
                resolve_org("bad-key")


class TestCreateUser:
    def test_creates_user(self, peewee_db: Path) -> None:
        tenant = create_tenant("Org")
        user = create_user("new@org.com", tenant)
        assert user.email == "new@org.com"
        assert str(user.tenant_id) == tenant.id
