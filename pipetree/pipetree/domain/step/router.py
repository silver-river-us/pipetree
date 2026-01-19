"""Router implementation."""

import time
from abc import abstractmethod
from collections.abc import Awaitable, Mapping
from typing import TYPE_CHECKING, ClassVar, Union, cast

from pipetree.domain.capability.capability import Capability
from pipetree.domain.step.step import Step
from pipetree.domain.types.context import Context

if TYPE_CHECKING:
    from pipetree.domain.pipeline.pipeline import Pipetree


class Router(Step):
    """
    Base class for router steps.

    Routes to different implementations based on context signals.
    The router itself maintains a stable capability contract.

    Subclasses can define `branch_outputs` to declare which context attributes
    each branch provides. Unselected branches will have their outputs set to
    empty dicts automatically.

    Example:
        class MyRouter(Router):
            branch_outputs = {
                "branch_a": ["result_a"],
                "branch_b": ["result_b", "extra_b"],
            }
    """

    # Override in subclass to declare branch -> context attribute mappings
    branch_outputs: ClassVar[dict[str, list[str]]] = {}

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

    def _get_unselected_branches(self, selected: str) -> list[str]:
        """Get names of branches NOT being taken."""
        return [k for k in self.table if k != selected]

    def _mark_branches_skipped(self, ctx: Context, selected: str) -> None:
        """Notify progress tracking that unselected branches are skipped."""
        notifier = getattr(ctx, "_notifier", None)
        if notifier and hasattr(notifier, "set_branch_skipped"):
            for branch_name in self._get_unselected_branches(selected):
                notifier.set_branch_skipped(branch_name)

    def _initialize_unselected_outputs(self, ctx: Context, selected: str) -> None:
        """Set empty dicts for outputs of unselected branches."""
        for branch_name, outputs in self.branch_outputs.items():
            if branch_name != selected:
                for attr_name in outputs:
                    setattr(ctx, attr_name, {})

    async def run(self, ctx: Context) -> Context:
        """Execute the selected route with progress tracking."""
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

        # Mark unselected branches as skipped and initialize their outputs
        self._mark_branches_skipped(ctx, route_key)
        self._initialize_unselected_outputs(ctx, route_key)

        target = self.table[route_key]
        notifier = getattr(ctx, "_notifier", None)

        # If target is a Pipetree, it handles its own progress tracking
        if isinstance(target, Pipetree):
            return await target.run(ctx)

        # If target is another Router, delegate to it
        if isinstance(target, Router):
            return await target.run(ctx)

        # For a single Step, handle progress reporting
        if notifier:
            notifier.step_started(target.name, ctx._step_index, ctx._total_steps)

        # Save and update step context for branch step
        old_step_name = getattr(ctx, "_step_name", None)
        ctx._step_name = target.name

        start_time = time.perf_counter()
        try:
            result = target.run(ctx)
            if hasattr(result, "__await__"):
                result = await cast(Awaitable[Context], result)

            duration = time.perf_counter() - start_time
            if notifier:
                notifier.step_completed(
                    target.name, ctx._step_index, ctx._total_steps, duration
                )

            return result
        except Exception as e:
            duration = time.perf_counter() - start_time
            if notifier:
                notifier.step_failed(
                    target.name, ctx._step_index, ctx._total_steps, duration, str(e)
                )
            raise
        finally:
            # Restore original step name
            if old_step_name is not None:
                ctx._step_name = old_step_name
