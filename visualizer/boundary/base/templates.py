from pathlib import Path

from fastapi.templating import Jinja2Templates

from boundary.formatters import (
    format_duration,
    format_timestamp,
    get_status_color,
    organize_steps_with_branches,
)

_templates: Jinja2Templates | None = None


def init_templates() -> Jinja2Templates:
    """Initialize templates with filters and globals."""
    from markupsafe import Markup

    global _templates
    # __file__ is visualizer/boundary/base/templates.py
    # assets are at visualizer/boundary/assets/
    assets_dir = Path(__file__).parent.parent / "assets"
    _templates = Jinja2Templates(directory=assets_dir / "templates")
    _templates.env.filters["format_duration"] = format_duration
    _templates.env.filters["format_timestamp"] = lambda ts: Markup(format_timestamp(ts))
    _templates.env.globals["get_status_color"] = get_status_color
    _templates.env.globals["organize_steps_with_branches"] = (
        organize_steps_with_branches
    )
    return _templates


def templates() -> Jinja2Templates:
    """Get the templates instance, initializing if needed."""
    if _templates is None:
        return init_templates()
    return _templates
