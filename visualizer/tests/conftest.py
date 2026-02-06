"""Shared test fixtures."""

import time

import pytest
from pathlib import Path
from sqlmodel import SQLModel, Session, create_engine

from pipetree.infrastructure.progress.models import Run, Step, Event
from pipetree.infrastructure.progress.models.database import _engines


@pytest.fixture
def pipetree_db(tmp_path: Path) -> Path:
    """Create a temp SQLite DB with pipetree schema (empty)."""
    db_file = tmp_path / "progress.db"
    engine = create_engine(f"sqlite:///{db_file}")
    SQLModel.metadata.create_all(engine)
    # Register in pipetree's engine cache so get_session finds it
    _engines[str(db_file)] = engine
    yield db_file
    _engines.pop(str(db_file), None)
    engine.dispose()


@pytest.fixture
def seeded_db(pipetree_db: Path) -> Path:
    """Pipetree DB seeded with sample runs, steps, and events."""
    engine = _engines[str(pipetree_db)]
    now = time.time()

    with Session(engine) as session:
        # Completed run
        run1 = Run(
            id="run-001",
            name="pipeline_a",
            started_at=now - 100,
            completed_at=now - 10,
            status="completed",
            total_steps=3,
        )
        session.add(run1)

        # Running run
        run2 = Run(
            id="run-002",
            name="pipeline_b",
            started_at=now - 50,
            status="running",
            total_steps=2,
        )
        session.add(run2)

        # Steps for run1
        for i, (name, status) in enumerate(
            [("load", "completed"), ("process", "completed"), ("save", "completed")]
        ):
            step = Step(
                run_id="run-001",
                name=name,
                step_index=i,
                status=status,
                started_at=now - 100 + i * 30,
                completed_at=now - 100 + (i + 1) * 30,
                duration_s=30.0,
                cpu_time_s=25.0,
                peak_mem_mb=128.0,
            )
            session.add(step)

        # Steps for run2 (one running)
        step_run2_0 = Step(
            run_id="run-002",
            name="fetch",
            step_index=0,
            status="completed",
            started_at=now - 50,
            completed_at=now - 30,
            duration_s=20.0,
            cpu_time_s=15.0,
            peak_mem_mb=64.0,
        )
        session.add(step_run2_0)

        step_run2_1 = Step(
            run_id="run-002",
            name="transform",
            step_index=1,
            status="running",
            started_at=now - 30,
        )
        session.add(step_run2_1)

        # Events for run2 step 1 (running step with progress)
        for j in range(3):
            evt = Event(
                run_id="run-002",
                timestamp=now - 30 + j * 5,
                step_name="transform",
                step_index=1,
                total_steps=2,
                event_type="progress",
                current=j + 1,
                total=10,
                message=f"Processing item {j + 1}",
            )
            session.add(evt)

        # A log event for run2 step 0
        log_evt = Event(
            run_id="run-002",
            timestamp=now - 40,
            step_name="fetch",
            step_index=0,
            total_steps=2,
            event_type="log",
            message="Fetching data",
        )
        session.add(log_evt)

        session.commit()

    return pipetree_db


@pytest.fixture
def peewee_db(tmp_path: Path) -> Path:
    """Initialize Peewee DB with auth tables."""
    from infra.db.db import db, init_db
    from lib.ctx.identity.tenant import Tenant
    from lib.ctx.identity.user import User
    from lib.ctx.auth.auth_code import AuthCode

    db_file = tmp_path / "db"
    init_db(db_file)
    db.create_tables([Tenant, User, AuthCode])
    yield db_file
    db.close()
