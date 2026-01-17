"""Step protocol definition."""

from collections.abc import Awaitable
from typing import Protocol, runtime_checkable

from pipetree.domain.capability.capability import Capability
from pipetree.domain.types.context import Context


@runtime_checkable
class Step(Protocol):
    """Protocol for pipeline steps."""

    cap: Capability
    name: str

    def run(self, ctx: Context) -> Context | Awaitable[Context]:
        """Execute the step, transforming context."""
        ...
