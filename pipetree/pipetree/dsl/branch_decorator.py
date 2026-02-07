"""Branch decorator for the DSL."""

from __future__ import annotations

from typing import Any, TypeVar

from pipetree.domain.step.step import Step

T = TypeVar("T", bound=type[Step])


def branch(branch_key: str) -> Any:
    """
    Decorator to mark which branch a step handles.

    Usage:
        @step(requires={"texts"}, provides={"processed_ops"})
        @branch("ops")
        class ProcessOps(Step):
            def run(self, ctx): ...
    """

    def decorator(cls: T) -> T:
        cls._dsl_branch = branch_key  # type: ignore[attr-defined]
        return cls

    return decorator
