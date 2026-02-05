"""
Pipetree Visualizer - Real-time monitoring dashboard.

A FastAPI application with WebSocket support for live progress updates.
Styled with Tailwind CSS and Flowbite, uses HTMX for dynamic updates.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware

from .controllers.admin_controller import router as admin_router
from .controllers.admin_controller import set_templates as set_admin_templates
from .controllers.login_controller import router as login_router
from .controllers.login_controller import set_templates as set_login_templates
from .infra.db import init_db, run_migrations
from .lib import (
    format_duration,
    format_timestamp,
    get_status_color,
    organize_steps_with_branches,
)
from .routes import register_routes

load_dotenv()

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
DATABASES_CONFIG_PATH = PROJECT_ROOT / "databases.json"

_default_db = PROJECT_ROOT / "examples" / "pdf_ingestion" / "db" / "progress.db"
DEFAULT_DB_PATH = Path(os.getenv("DB_PATH", str(_default_db)))


def load_databases() -> list[dict]:
    """Load the list of configured databases."""
    if DATABASES_CONFIG_PATH.exists():
        with open(DATABASES_CONFIG_PATH) as f:
            config = json.load(f)
            databases = config.get("databases", [])
            # Resolve relative paths to absolute
            for db in databases:
                db_path = Path(db["path"])
                if not db_path.is_absolute():
                    db["path"] = str(PROJECT_ROOT / db_path)
                db["exists"] = Path(db["path"]).exists()
            return databases
    return []


def save_databases(databases: list[dict]) -> None:
    """Save the list of configured databases."""
    # Convert absolute paths back to relative for storage
    save_data = []
    for db in databases:
        db_path = Path(db["path"])
        try:
            relative_path = db_path.relative_to(PROJECT_ROOT)
            save_data.append({"name": db["name"], "path": str(relative_path)})
        except ValueError:
            # Path is not relative to project root, keep absolute
            save_data.append({"name": db["name"], "path": str(db_path)})

    with open(DATABASES_CONFIG_PATH, "w") as f:
        json.dump({"databases": save_data}, f, indent=2)


def add_database(name: str, path: str) -> dict:
    """Add a new database to the configuration."""
    databases = load_databases()
    new_db = {"name": name, "path": path, "exists": Path(path).exists()}
    databases.append(new_db)
    save_databases(databases)
    return new_db


def remove_database(path: str) -> bool:
    """Remove a database from the configuration."""
    databases = load_databases()
    original_len = len(databases)
    databases = [db for db in databases if db["path"] != path]
    if len(databases) < original_len:
        save_databases(databases)
        return True
    return False


# Create FastAPI app
app = FastAPI(title="Pipetree Visualizer", version="1.0.0")


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        from .controllers.login_controller import get_current_user

        request.state.user = get_current_user(request)
        return await call_next(request)


app.add_middleware(AuthMiddleware)


@app.on_event("startup")
def startup():
    init_db()
    run_migrations()


# Templates
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

# Add template filters and globals
templates.env.filters["format_duration"] = format_duration
templates.env.filters["format_timestamp"] = format_timestamp
templates.env.globals["get_status_color"] = get_status_color
templates.env.globals["organize_steps_with_branches"] = organize_steps_with_branches

# Static files
app.mount(
    "/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static"
)

# Register admin + login routers
set_admin_templates(templates)
set_login_templates(templates)
app.include_router(admin_router)
app.include_router(login_router)

# Register all routes
register_routes(app, templates, DEFAULT_DB_PATH)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
