"""Router protocol definition."""

from collections.abc import Mapping
from typing import TYPE_CHECKING, Protocol, Union, runtime_checkable

from ingestion.domain.step.step_protocol import Step
from ingestion.domain.types.context import Ctx

if TYPE_CHECKING:
    from ingestion.domain.pipeline.pipeline import Pipeline


@runtime_checkable
class Router(Step, Protocol):
    """
    Protocol for router steps that branch to different implementations.

    Routers keep a stable capability while selecting a target step/pipeline
    based on signals in the context.
    """

    table: Mapping[str, Union[Step, "Pipeline"]]

    def pick(self, ctx: Ctx) -> str:
        """Select which route to take based on context."""
        ...
