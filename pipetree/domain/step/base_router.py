"""Base router implementation."""

from abc import abstractmethod
from collections.abc import Awaitable, Mapping
from typing import TYPE_CHECKING, Union, cast

from pipetree.domain.capability.capability import Capability
from pipetree.domain.step.base_step import BaseStep
from pipetree.domain.step.step import Step
from pipetree.domain.types.context import Context

if TYPE_CHECKING:
    from pipetree.domain.pipeline.pipeline import Pipetree


class BaseRouter(BaseStep):
    """
    Base class for router steps.

    Routes to different implementations based on context signals.
    The router itself maintains a stable capability contract.
    """

    def __init__(
        self,
        cap: Capability,
        name: str,
        table: Mapping[str, Union[Step, "Pipetree"]],
        default: str | None = None,
    ) -> None:
        super().__init__(cap, name)
        self.table = table
        self.default = default

    @abstractmethod
    def pick(self, ctx: Context) -> str:
        """Select which route to take based on context."""
        ...

    async def run(self, ctx: Context) -> Context:
        """Execute the selected route."""
        from pipetree.domain.pipeline.pipeline import Pipetree

        route_key = self.pick(ctx)
        if route_key not in self.table:
            if self.default is not None:
                route_key = self.default
            else:
                raise ValueError(
                    f"Router {self.name} picked unknown route {route_key!r}. "
                    f"Available: {list(self.table.keys())}"
                )

        target = self.table[route_key]

        if isinstance(target, Pipetree):
            return await target.run(ctx)
        else:
            result = target.run(ctx)
            if hasattr(result, "__await__"):
                return await cast(Awaitable[Context], result)
            return result
