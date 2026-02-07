from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from peewee import CharField, DatabaseProxy, DateTimeField, Model, SqliteDatabase

db = DatabaseProxy()


def init_db(db_path: Path | None = None):
    """Initialize the visualizer system database."""
    if db_path is None:
        from config import settings

        db_path = settings.default_db_path / "visualizer.db"

    db_path.parent.mkdir(parents=True, exist_ok=True)

    database = SqliteDatabase(
        str(db_path),
        pragmas={
            "journal_mode": "wal",
            "foreign_keys": 1,
        },
    )

    db.initialize(database)
    db.connect(reuse_if_open=True)


def run_migrations():
    """Run pending database migrations."""
    from peewee_migrate import Router
    migrations_dir = Path(__file__).parent / "migrations"
    router = Router(db.obj, migrate_dir=str(migrations_dir))
    router.run()


def generate_uuid() -> str:
    return uuid4().hex


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class BaseModel(Model):
    id = CharField(primary_key=True, max_length=32, default=generate_uuid)
    created_at = DateTimeField(default=utcnow)
    updated_at = DateTimeField(default=utcnow)

    class Meta:
        database = db

    @classmethod
    def find_by(cls, **kwargs):
        expressions = [getattr(cls, k) == v for k, v in kwargs.items()]
        return cls.get_or_none(*expressions)

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_uuid()

        self.updated_at = datetime.now(UTC).replace(tzinfo=None)
        return super().save(*args, **kwargs)
