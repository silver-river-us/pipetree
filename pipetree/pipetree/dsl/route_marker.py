"""Route marker for the DSL."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pipetree.dsl.branch_target import BranchTarget


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
        from pipetree.dsl.branch_target import BranchTarget

        if isinstance(branches, list):
            return RouteMarker(key=self.key, branches=branches, default=self.default)
        # Chained route: this route becomes a branch target
        return BranchTarget(key=self.key, target=branches)

    def __repr__(self) -> str:
        return f"route({self.key!r})"


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
