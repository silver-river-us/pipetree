"""Tests for visualizer.lib.admin."""

from pathlib import Path

from visualizer.lib.admin import (
    create_tenant,
    create_user,
    delete_tenant,
    get_tenant,
    get_user_by_email,
    list_tenants,
    list_users_for_tenant,
)


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


class TestCreateTenant:
    def test_auto_slug_and_api_key(self, peewee_db: Path) -> None:
        tenant = create_tenant("My Org")
        assert tenant.slug == "my-org"
        assert len(tenant.api_key) > 0
        assert tenant.db_name == "my-org"

    def test_custom_db_name(self, peewee_db: Path) -> None:
        tenant = create_tenant("Test Org", db_name="custom.db")
        assert tenant.db_name == "custom.db"


class TestDeleteTenant:
    def test_existing(self, peewee_db: Path) -> None:
        tenant = create_tenant("To Delete")
        assert delete_tenant(tenant.id) is True
        assert get_tenant(tenant.id) is None

    def test_nonexistent(self, peewee_db: Path) -> None:
        assert delete_tenant("no-such-id") is False

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


class TestCreateUser:
    def test_creates_user(self, peewee_db: Path) -> None:
        tenant = create_tenant("Org")
        user = create_user("new@org.com", tenant)
        assert user.email == "new@org.com"
        assert str(user.tenant_id) == tenant.id
