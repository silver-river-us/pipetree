"""Base step implementation."""

from abc import ABC, abstractmethod
from collections.abc import Awaitable

from ingestion.domain.capability.capability import Capability
from ingestion.domain.types.context import Ctx


class BaseStep(ABC):
    """Base class for implementing steps."""

    def __init__(self, cap: Capability, name: str) -> None:
        self.cap = cap
        self.name = name

    @abstractmethod
    def run(self, ctx: Ctx) -> Ctx | Awaitable[Ctx]:
        """Execute the step, transforming context."""
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, cap={self.cap.name!r})"
