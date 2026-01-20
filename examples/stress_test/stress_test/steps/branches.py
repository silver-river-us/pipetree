"""Branch steps for the stress test pipeline."""

import asyncio
import random

from pipetree import Step, step

from ..context import StressTestContext


@step(requires={"quality_score"}, provides={"branch_a_result"})
class ProcessHighQuality(Step):
    """Process high quality results."""

    async def run(self, ctx: StressTestContext) -> StressTestContext:
        print("    [Branch: HIGH] Processing high quality results...")

        for i in range(5):
            await asyncio.sleep(random.uniform(0.1, 0.2))
            ctx.report_progress(i + 1, 5, f"High quality processing {i + 1}/5")

        ctx.branch_a_result = {
            "quality": "high",
            "score": ctx.quality_score,
            "action": "fast_track",
            "processed": True,
        }

        return ctx


@step(requires={"quality_score"}, provides={"branch_b_result"})
class ProcessMediumQuality(Step):
    """Process medium quality results."""

    async def run(self, ctx: StressTestContext) -> StressTestContext:
        print("    [Branch: MEDIUM] Processing medium quality results...")

        for i in range(7):
            await asyncio.sleep(random.uniform(0.1, 0.25))
            ctx.report_progress(i + 1, 7, f"Medium quality processing {i + 1}/7")

        ctx.branch_b_result = {
            "quality": "medium",
            "score": ctx.quality_score,
            "action": "standard_review",
            "processed": True,
        }

        return ctx


@step(requires={"quality_score"}, provides={"branch_c_result"})
class ProcessLowQuality(Step):
    """Process low quality results with extra validation."""

    async def run(self, ctx: StressTestContext) -> StressTestContext:
        print(
            "    [Branch: LOW] Processing low quality results with extra validation..."
        )

        for i in range(10):
            await asyncio.sleep(random.uniform(0.15, 0.3))
            ctx.report_progress(i + 1, 10, f"Low quality validation {i + 1}/10")

        ctx.branch_c_result = {
            "quality": "low",
            "score": ctx.quality_score,
            "action": "manual_review_required",
            "processed": True,
            "warnings": ["Quality below threshold", "Manual review recommended"],
        }

        return ctx
