"""Router that directs to ops or parts processing based on category."""

from pipetree import Router
from pipetree.types import Context


class CategoryRouter(Router):
    """
    Routes to different processing pipelines based on document category.

    Routes:
    - "ops": Operations manual processing
    - "parts": Parts catalog processing
    """

    def pick(self, ctx: Context) -> str:
        """Select route based on the category determined by CategorizeStep."""
        category: str | None = getattr(ctx, "category", None)

        if category is None:
            raise ValueError("Category not set in context. Run CategorizeStep first.")

        print(f"Routing to: {category.upper()} processing branch")
        return category

    async def run(self, ctx: Context) -> Context:
        """Execute the selected route and mark skipped branches."""
        import time
        from collections.abc import Awaitable
        from typing import cast

        from pipetree.domain.pipeline.pipeline import Pipetree

        # Get the route key (pick will be called by parent, but we need it here too)
        route_key = getattr(ctx, "category", None)
        if route_key not in self.table and self.default:
            route_key = self.default

        notifier = getattr(ctx, "_notifier", None)

        # Mark unselected branches as skipped
        if notifier and hasattr(notifier, "set_branch_skipped"):
            for branch_name in self.table.keys():
                if branch_name != route_key:
                    notifier.set_branch_skipped(branch_name)

        # Set empty dicts for unselected branch outputs
        if route_key == "parts":
            ctx.processed_ops = {}  # type: ignore
        elif route_key == "ops":
            ctx.processed_parts = {}  # type: ignore
            ctx.processed_mechanical = {}  # type: ignore
            ctx.processed_electrical = {}  # type: ignore

        # Run the selected branch with proper progress reporting
        target = self.table[route_key]

        if isinstance(target, Pipetree):
            return await target.run(ctx)

        # Check if target is a Router (nested routing)
        if isinstance(target, Router):
            return await target.run(ctx)

        # For a Step, manually handle the progress reporting
        if notifier:
            # Report step started for the branch step
            notifier.step_started(target.name, ctx._step_index, ctx._total_steps)

        # Save and update step context for branch step
        old_step_name = ctx._step_name
        ctx._step_name = target.name

        start_time = time.perf_counter()
        try:
            result = target.run(ctx)
            if hasattr(result, "__await__"):
                result = await cast(Awaitable[Context], result)

            duration = time.perf_counter() - start_time
            if notifier:
                notifier.step_completed(target.name, ctx._step_index, ctx._total_steps, duration)

            return result
        except Exception as e:
            duration = time.perf_counter() - start_time
            if notifier:
                notifier.step_failed(target.name, ctx._step_index, ctx._total_steps, duration, str(e))
            raise
        finally:
            # Restore original step name
            ctx._step_name = old_step_name
