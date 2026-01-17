"""Step protocol definition."""

from collections.abc import Awaitable
from typing import Protocol, runtime_checkable

from ingestion.domain.capability.capability import Capability
from ingestion.domain.types.context import Ctx


@runtime_checkable
class Step(Protocol):
    """Protocol for pipeline steps."""

    cap: Capability
    name: str

    def run(self, ctx: Ctx) -> Ctx | Awaitable[Ctx]:
        """Execute the step, transforming context."""
        ...
