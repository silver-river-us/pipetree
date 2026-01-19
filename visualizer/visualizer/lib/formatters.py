"""Formatting and helper functions for templates."""

import datetime
from typing import Any


def format_duration(seconds: float | None) -> str:
    """Format duration in human-readable form."""
    if seconds is None:
        return "-"
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    if seconds < 60:
        return f"{seconds:.2f}s"
    if seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.0f}s"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    if secs > 0:
        return f"{hours}h {minutes}m {secs:.0f}s"
    return f"{hours}h {minutes}m"


def format_timestamp(ts: float | None) -> str:
    """Format timestamp as time string (12-hour format)."""
    if ts is None:
        return "-"
    dt = datetime.datetime.fromtimestamp(ts)
    return dt.strftime("%I:%M:%S %p").lstrip("0")


def get_status_color(status: str) -> dict[str, str]:
    """Get Tailwind color classes for a status."""
    colors = {
        "pending": {
            "bg": "bg-gray-100",
            "text": "text-gray-600",
            "border": "border-gray-300",
            "icon": "clock",
        },
        "running": {
            "bg": "bg-blue-100",
            "text": "text-blue-600",
            "border": "border-blue-400",
            "icon": "play",
        },
        "completed": {
            "bg": "bg-green-100",
            "text": "text-green-600",
            "border": "border-green-400",
            "icon": "check",
        },
        "failed": {
            "bg": "bg-red-100",
            "text": "text-red-600",
            "border": "border-red-400",
            "icon": "x",
        },
        "skipped": {
            "bg": "bg-gray-50",
            "text": "text-gray-400",
            "border": "border-gray-200",
            "icon": "skip",
        },
    }
    return colors.get(status, colors["pending"])


def organize_steps_with_branches(steps: list[dict]) -> dict:
    """Organize steps into main path and nested branch tree."""
    main_steps = []
    branches_by_parent: dict[str, dict[str, list[dict]]] = {}

    for step in steps:
        branch = step.get("branch")
        parent = step.get("parent_step")
        if branch and parent:
            if parent not in branches_by_parent:
                branches_by_parent[parent] = {}
            if branch not in branches_by_parent[parent]:
                branches_by_parent[parent][branch] = []
            branches_by_parent[parent][branch].append(step)
        else:
            main_steps.append(step)

    def build_branch_tree(parent_name: str) -> dict[str, Any]:
        """Recursively build branch tree."""
        if parent_name not in branches_by_parent:
            return {}
        result = {}
        for branch_name, branch_steps in branches_by_parent[parent_name].items():
            result[branch_name] = {
                "steps": branch_steps,
                "children": {},
            }
            for step in branch_steps:
                step_name = step.get("name", "")
                if step_name in branches_by_parent:
                    result[branch_name]["children"] = build_branch_tree(step_name)
        return result

    main_router = None
    for step in main_steps:
        step_name = step.get("name", "")
        if step_name.startswith("route_") and step_name in branches_by_parent:
            main_router = step_name
            break

    branch_tree = build_branch_tree(main_router) if main_router else {}

    flat_branches: dict[str, list[dict]] = {}
    for parent_branches in branches_by_parent.values():
        for branch_name, branch_steps in parent_branches.items():
            if branch_name not in flat_branches:
                flat_branches[branch_name] = []
            flat_branches[branch_name].extend(branch_steps)

    return {
        "main": main_steps,
        "branches": flat_branches,
        "branch_tree": branch_tree,
        "branches_by_parent": branches_by_parent,
    }
