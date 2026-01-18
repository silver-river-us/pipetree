"""Router that further categorizes parts into mechanical vs electrical."""

import time

from pipetree import Router
from pipetree.types import Context


class PartsTypeRouter(Router):
    """
    Routes parts processing based on part type detection.

    Routes:
    - "mechanical": Mechanical parts (gears, bearings, housings)
    - "electrical": Electrical parts (wiring, connectors, circuits)
    """

    def pick(self, ctx: Context) -> str:
        """Detect part type from text content."""
        texts: list[str] = getattr(ctx, "texts", [])
        full_text = "\n".join(texts).lower()

        # Count indicators
        mechanical_indicators = sum(1 for word in [
            "gear", "bearing", "shaft", "housing", "bolt", "nut", "washer",
            "spring", "seal", "gasket", "bushing", "coupling", "bracket"
        ] if word in full_text)

        electrical_indicators = sum(1 for word in [
            "wire", "cable", "connector", "circuit", "relay", "fuse",
            "switch", "terminal", "harness", "sensor", "motor", "solenoid"
        ] if word in full_text)

        part_type = "mechanical" if mechanical_indicators >= electrical_indicators else "electrical"
        print(f"  Part type detected: {part_type.upper()}")
        print(f"    Mechanical indicators: {mechanical_indicators}, Electrical: {electrical_indicators}")

        return part_type

    async def run(self, ctx: Context) -> Context:
        """Execute the selected route and mark skipped branches."""
        from collections.abc import Awaitable
        from typing import cast

        from pipetree.domain.pipeline.pipeline import Pipetree

        route_key = self.pick(ctx)

        notifier = getattr(ctx, "_notifier", None)

        # Mark unselected branches as skipped
        if notifier and hasattr(notifier, "set_branch_skipped"):
            for branch_name in self.table.keys():
                if branch_name != route_key:
                    notifier.set_branch_skipped(branch_name)

        # Run the selected branch with proper progress reporting
        target = self.table[route_key]

        if isinstance(target, Pipetree):
            return await target.run(ctx)

        # For a Step, manually handle the progress reporting
        if notifier:
            notifier.step_started(target.name, ctx._step_index, ctx._total_steps)

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
            ctx._step_name = old_step_name
