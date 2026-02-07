"""Database engine and session management for progress tracking."""

from pathlib import Path

from sqlmodel import Session, create_engine

# Cache engines by path to avoid creating multiple engines for the same db
_engines: dict[str, object] = {}


def get_engine(db_path: Path):  # type: ignore[no-untyped-def]
    """Get or create a SQLAlchemy engine for the given database path."""
    path_str = str(db_path)
    if path_str not in _engines:
        _engines[path_str] = create_engine(
            f"sqlite:///{path_str}",
            connect_args={"check_same_thread": False},
        )
    return _engines[path_str]


def get_session(db_path: Path) -> Session:
    """Create a new session for the given database path."""
    engine = get_engine(db_path)
    return Session(engine)
