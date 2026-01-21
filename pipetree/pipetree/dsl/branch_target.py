"""Branch target marker for the DSL."""

from __future__ import annotations

from dataclasses import dataclass
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
        from pipetree.dsl.route_marker import RouteMarker

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
