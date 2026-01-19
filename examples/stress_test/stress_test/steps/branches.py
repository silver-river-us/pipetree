"""Branch steps for the stress test pipeline."""

import asyncio
import random
from typing import ClassVar

from pipetree import Router, Step

from ..context import StressTestContext


class QualityRouter(Router):
    """Route based on quality score."""

    # Declare which context attributes each branch provides
    branch_outputs: ClassVar[dict[str, list[str]]] = {
        "high": ["branch_a_result"],
        "medium": ["branch_b_result"],
        "low": ["branch_c_result"],
    }

    def pick(self, ctx: StressTestContext) -> str:
        """Select branch based on quality score."""
        if ctx.quality_score >= 0.9:
            return "high"
        elif ctx.quality_score >= 0.8:
            return "medium"
        else:
            return "low"


class ProcessHighQualityStep(Step):
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


class ProcessMediumQualityStep(Step):
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


class ProcessLowQualityStep(Step):
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
