"""
Pipetree Visualizer - Real-time pipeline monitoring dashboard.

A FastAPI application with WebSocket support for live progress updates.
Styled with Tailwind CSS and Flowbite, uses HTMX for dynamic updates.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .lib import (
    format_duration,
    format_timestamp,
    get_status_color,
    organize_steps_with_branches,
)
from .routes import register_routes

load_dotenv()

# Configuration
_default_db = (
    Path(__file__).parent.parent / "examples" / "pdf_ingestion" / "db" / "progress.db"
)
DEFAULT_DB_PATH = Path(os.getenv("DB_PATH", str(_default_db)))

# Create FastAPI app
app = FastAPI(title="Pipetree Visualizer", version="1.0.0")

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

# Register all routes
register_routes(app, templates, DEFAULT_DB_PATH)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
