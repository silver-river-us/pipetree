"""Create auth_codes table for email verification codes."""


def migrate(migrator, database, **kwargs):
    database.execute_sql("""
        CREATE TABLE auth_codes (
            id VARCHAR(32) PRIMARY KEY,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            email VARCHAR(255) NOT NULL,
            code VARCHAR(6) NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            used BOOLEAN NOT NULL DEFAULT 0
        )
    """)

    database.execute_sql("CREATE INDEX idx_auth_codes_email ON auth_codes(email)")


def rollback(migrator, database, **kwargs):
    database.execute_sql("DROP TABLE IF EXISTS auth_codes;")
