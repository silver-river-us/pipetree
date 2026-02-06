"""Boundary layer - HTTP controllers and assets."""

from boundary.controllers.api.v1.benchmarks_controller import (
    router as api_benchmarks_router,
)
from boundary.controllers.api.v1.databases_controller import (
    router as api_databases_router,
)
from boundary.controllers.api.v1.ingest_controller import (
    router as ingest_router,
)
from boundary.controllers.api.v1.runs_controller import (
    router as api_runs_router,
)
from boundary.controllers.api.v1.telemetry_controller import (
    router as api_telemetry_router,
)
from boundary.controllers.web.admin_controller import (
    router as admin_router,
)
from boundary.controllers.web.benchmarks_controller import (
    router as benchmarks_router,
)
from boundary.controllers.web.dashboard_controller import (
    router as dashboard_router,
)
from boundary.controllers.web.login_controller import (
    router as login_router,
)
from boundary.controllers.web.runs_controller import (
    router as runs_router,
)
from boundary.controllers.web.steps_controller import (
    router as steps_router,
)
from boundary.controllers.web.telemetry_controller import (
    router as telemetry_router,
)
from boundary.controllers.web.websocket_controller import (
    router as websocket_router,
)

__all__ = [
    "admin_router",
    "api_benchmarks_router",
    "api_databases_router",
    "api_runs_router",
    "api_telemetry_router",
    "benchmarks_router",
    "dashboard_router",
    "ingest_router",
    "login_router",
    "runs_router",
    "steps_router",
    "telemetry_router",
    "websocket_router",
]
