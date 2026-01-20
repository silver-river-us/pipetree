"""Route markers for the DSL."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BranchTarget:
    """
    A branch key pointing to a target step or nested route.

    Created by: ops >> process_ops
    Or: parts >> parts_type >> [...]
    """

    key: str
    target: Any = None

    def __rshift__(self, target: Any) -> BranchTarget:
        """
        Allow: ops >> step or ops >> route >> [...]

        Handle chaining like: B("parts") >> parts_type >> [...]
        where parts_type is a RouteMarker.
        """
        if isinstance(self.target, RouteMarker) and isinstance(target, list):
            # Chained: B("parts") >> parts_type >> [branches]
            # Apply branches to the existing RouteMarker
            filled_route = RouteMarker(
                key=self.target.key,
                branches=target,
                default=self.target.default,
            )
            return BranchTarget(key=self.key, target=filled_route)
        return BranchTarget(key=self.key, target=target)

    def __repr__(self) -> str:
        return f"{self.key} >> {self.target!r}"


@dataclass
class RouteMarker:
    """
    Marker for defining routes in the DSL.

    Created by using >> on a route key:
        category >> [step1, step2]
    """

    key: str
    branches: list[Any] = field(default_factory=list)
    default: str | None = None

    def __rshift__(
        self, branches: list[Any] | BranchTarget
    ) -> RouteMarker | BranchTarget:
        """
        Allow:
            category >> [step1, step2]
            parts >> parts_type >> [...]  (chained routes)
        """
        if isinstance(branches, list):
            return RouteMarker(key=self.key, branches=branches, default=self.default)
        # Chained route: this route becomes a branch target
        return BranchTarget(key=self.key, target=branches)

    def __repr__(self) -> str:
        return f"route({self.key!r})"


def B(key: str) -> BranchTarget:
    """
    Create a branch marker for explicit branch assignment.

    Usage:
        category >> [
            B("ops") >> process_ops,
            B("parts") >> parts_type >> [...],
        ]

    Short for "Branch" - keeps the DSL concise.
    """
    return BranchTarget(key=key)


def route(key: str, default: str | None = None) -> RouteMarker:
    """
    Create a route marker for the DSL.

    Usage:
        route("category") >> [process_ops, process_parts]

    Or use a pre-defined route variable:
        category = route("category")
        category >> [process_ops, process_parts]
    """
    return RouteMarker(key=key, default=default)
