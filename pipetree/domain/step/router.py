"""Router protocol definition."""

from collections.abc import Mapping
from typing import TYPE_CHECKING, Protocol, Union, runtime_checkable

from pipetree.domain.step.step import Step
from pipetree.domain.types.context import Context

if TYPE_CHECKING:
    from pipetree.domain.pipeline.pipeline import Pipetree


@runtime_checkable
class Router(Step, Protocol):
    """
    Protocol for router steps that branch to different implementations.

    Routers keep a stable capability while selecting a target step/pipeline
    based on signals in the context.
    """

    table: Mapping[str, Union[Step, "Pipetree"]]

    def pick(self, ctx: Context) -> str:
        """Select which route to take based on context."""
        ...
