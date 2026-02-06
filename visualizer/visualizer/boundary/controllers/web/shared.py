"""Shared utilities for web controllers."""

from pathlib import Path

from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from visualizer.lib import (
    format_duration,
    format_timestamp,
    get_status_color,
    organize_steps_with_branches,
)
from visualizer.lib.auth import get_current_user

_templates: Jinja2Templates | None = None


def init_templates() -> Jinja2Templates:
    """Initialize templates with filters and globals."""
    from markupsafe import Markup

    global _templates
    # __file__ is visualizer/boundary/controllers/web/shared.py
    # assets are at visualizer/boundary/assets/
    assets_dir = Path(__file__).parent.parent.parent / "assets"
    _templates = Jinja2Templates(directory=assets_dir / "templates")
    _templates.env.filters["format_duration"] = format_duration
    _templates.env.filters["format_timestamp"] = lambda ts: Markup(format_timestamp(ts))
    _templates.env.globals["get_status_color"] = get_status_color
    _templates.env.globals["organize_steps_with_branches"] = organize_steps_with_branches
    return _templates


def templates() -> Jinja2Templates:
    """Get the templates instance, initializing if needed."""
    if _templates is None:
        return init_templates()
    return _templates


def get_db_path(db: str | None, request: Request | None = None) -> Path:
    """Get database path from explicit param or logged-in tenant."""
    from visualizer.lib.admin import get_tenant

    from visualizer.config import settings

    if db:
        return Path(db)
    if request:
        user = get_current_user(request)
        if user and user.get("tenant_id"):
            tenant = get_tenant(user["tenant_id"])
            if tenant:
                return settings.default_db_path / tenant.db_name
    return settings.default_db_path


def get_template_context(db_path: Path) -> dict:
    """Get common template context."""
    return {
        "databases": [],
        "current_db": str(db_path),
    }


def require_login(request: Request) -> RedirectResponse | None:
    """Return redirect response if not authenticated, else None."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return None
