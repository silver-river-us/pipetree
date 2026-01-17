"""Base step implementation."""

from abc import ABC, abstractmethod
from collections.abc import Awaitable

from pipetree.domain.capability.capability import Capability
from pipetree.domain.types.context import Context


class BaseStep(ABC):
    """Base class for implementing steps."""

    def __init__(self, cap: Capability, name: str) -> None:
        self.cap = cap
        self.name = name

    @abstractmethod
    def run(self, ctx: Context) -> Context | Awaitable[Context]:
        """Execute the step, transforming context."""
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, cap={self.cap.name!r})"
