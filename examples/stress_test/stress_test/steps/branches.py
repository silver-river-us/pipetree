"""Branch steps for the stress test pipeline."""

import asyncio
import random

from pipetree import Router, Step

from ..context import StressTestContext


class QualityRouter(Router):
    """Route based on quality score."""

    def pick(self, ctx: StressTestContext) -> str:
        """Select branch based on quality score."""
        if ctx.quality_score >= 0.9:
            return "high"
        elif ctx.quality_score >= 0.8:
            return "medium"
        else:
            return "low"

    async def run(self, ctx: StressTestContext) -> StressTestContext:
        """Execute the selected route and set empty results for unselected branches."""
        import time
        from collections.abc import Awaitable
        from typing import cast

        from pipetree.domain.pipeline.pipeline import Pipetree

        # Get the route key
        route_key = self.pick(ctx)
        if route_key not in self.table and self.default:
            route_key = self.default

        # Set empty dicts for unselected branch outputs
        if route_key != "high":
            ctx.branch_a_result = {}
        if route_key != "medium":
            ctx.branch_b_result = {}
        if route_key != "low":
            ctx.branch_c_result = {}

        notifier = getattr(ctx, "_notifier", None)

        # Mark unselected branches as skipped
        if notifier and hasattr(notifier, "set_branch_skipped"):
            for branch_name in self.table:
                if branch_name != route_key:
                    notifier.set_branch_skipped(branch_name)

        # Run the selected branch
        target = self.table[route_key]

        if isinstance(target, Pipetree):
            return await target.run(ctx)

        if isinstance(target, Router):
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
                result = await cast(Awaitable[StressTestContext], result)

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


class ProcessHighQualityStep(Step):
    """Process high quality results."""

    async def run(self, ctx: StressTestContext) -> StressTestContext:
        print("    [Branch: HIGH] Processing high quality results...")

        for i in range(5):
            await asyncio.sleep(random.uniform(0.1, 0.2))
            ctx.report_progress(i + 1,5,f"High quality processing {i + 1}/5")

        ctx.branch_a_result = {
            "quality": "high",
            "score": ctx.quality_score,
            "action": "fast_track",
            "processed": True,
        }

        return ctx


class ProcessMediumQualityStep(Step):
    """Process medium quality results."""

    async def run(self, ctx: StressTestContext) -> StressTestContext:
        print("    [Branch: MEDIUM] Processing medium quality results...")

        for i in range(7):
            await asyncio.sleep(random.uniform(0.1, 0.25))
            ctx.report_progress(i + 1,7,f"Medium quality processing {i + 1}/7")

        ctx.branch_b_result = {
            "quality": "medium",
            "score": ctx.quality_score,
            "action": "standard_review",
            "processed": True,
        }

        return ctx


class ProcessLowQualityStep(Step):
    """Process low quality results with extra validation."""

    async def run(self, ctx: StressTestContext) -> StressTestContext:
        print("    [Branch: LOW] Processing low quality results with extra validation...")

        for i in range(10):
            await asyncio.sleep(random.uniform(0.15, 0.3))
            ctx.report_progress(i + 1,10,f"Low quality validation {i + 1}/10")

        ctx.branch_c_result = {
            "quality": "low",
            "score": ctx.quality_score,
            "action": "manual_review_required",
            "processed": True,
            "warnings": ["Quality below threshold", "Manual review recommended"],
        }

        return ctx
