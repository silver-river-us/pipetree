"""Step decorator for the DSL."""

from __future__ import annotations

from typing import Any, TypeVar

from pipetree.domain.capability.capability import Capability
from pipetree.domain.step.step import Step

T = TypeVar("T", bound=type[Step])


def _to_snake_case(name: str) -> str:
    """Convert CamelCase to snake_case."""
    result = []
    for i, char in enumerate(name):
        if char.isupper() and i > 0:
            result.append("_")
        result.append(char.lower())
    return "".join(result)


def step(
    requires: set[str] | None = None,
    provides: set[str] | None = None,
    name: str | None = None,
) -> Any:
    """
    Decorator to define a step with its capability inline.

    Usage:
        @step(requires={"path"}, provides={"pdf"})
        class LoadPdf(Step):
            def run(self, ctx): ...

    The capability name defaults to the snake_case version of the class name.
    """

    def decorator(cls: T) -> T:
        # Derive name from class name if not provided
        cap_name = name or _to_snake_case(cls.__name__)

        # Store capability info on the class (dynamic attributes for decorator pattern)
        cls._dsl_capability = Capability(  # type: ignore[attr-defined]
            name=cap_name, requires=requires or set(), provides=provides or set()
        )
        cls._dsl_name = cap_name  # type: ignore[attr-defined]

        return cls

    return decorator
