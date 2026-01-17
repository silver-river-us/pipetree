"""Base router implementation."""

from abc import abstractmethod
from collections.abc import Awaitable, Mapping
from typing import TYPE_CHECKING, Union, cast

from ingestion.domain.capability.capability import Capability
from ingestion.domain.step.base_step import BaseStep
from ingestion.domain.step.step_protocol import Step
from ingestion.domain.types.context import Ctx

if TYPE_CHECKING:
    from ingestion.domain.pipeline.pipeline import Pipeline


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
        table: Mapping[str, Union[Step, "Pipeline"]],
        default: str | None = None,
    ) -> None:
        super().__init__(cap, name)
        self.table = table
        self.default = default

    @abstractmethod
    def pick(self, ctx: Ctx) -> str:
        """Select which route to take based on context."""
        ...

    async def run(self, ctx: Ctx) -> Ctx:
        """Execute the selected route."""
        from ingestion.domain.pipeline.pipeline import Pipeline

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

        if isinstance(target, Pipeline):
            return await target.run_with_ctx(ctx)
        else:
            result = target.run(ctx)
            if hasattr(result, "__await__"):
                return await cast(Awaitable[Ctx], result)
            return result
