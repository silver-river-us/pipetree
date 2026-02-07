"""Create tenants and users tables."""


def migrate(migrator, database, **kwargs):
    database.execute_sql("""
        CREATE TABLE tenants (
            id VARCHAR(32) PRIMARY KEY,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            name VARCHAR(255) NOT NULL,
            slug VARCHAR(63) NOT NULL UNIQUE,
            api_key VARCHAR(64) NOT NULL UNIQUE,
            db_name VARCHAR(255) NOT NULL
        )
    """)
    database.execute_sql("CREATE INDEX idx_tenants_slug ON tenants(slug)")
    database.execute_sql("CREATE INDEX idx_tenants_api_key ON tenants(api_key)")
    database.execute_sql("""
        CREATE TABLE users (
            id VARCHAR(32) PRIMARY KEY,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            email VARCHAR(255) NOT NULL UNIQUE,
            tenant_id VARCHAR(32) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE
        )
    """)
    database.execute_sql("CREATE INDEX idx_users_email ON users(email)")
    database.execute_sql("CREATE INDEX idx_users_tenant_id ON users(tenant_id)")


def rollback(migrator, database, **kwargs):
    database.execute_sql("DROP TABLE IF EXISTS users;")
    database.execute_sql("DROP TABLE IF EXISTS tenants;")
