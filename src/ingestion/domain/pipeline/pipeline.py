"""Pipeline orchestrator with contract validation."""

import asyncio
import inspect
from typing import TYPE_CHECKING, Optional

from ingestion.domain.pipeline.errors import ContractViolationError
from ingestion.domain.step.step_protocol import Step
from ingestion.domain.types.context import Ctx
from ingestion.domain.types.cursor import Cursor

if TYPE_CHECKING:
    from ingestion.infrastructure.checkpoint.checkpoint_store import CheckpointStore


class Pipeline:
    """
    Pipeline orchestrator that runs steps sequentially with contract validation.

    Features:
    - Validates preconditions before each step
    - Validates postconditions after each step
    - Supports both sync and async steps transparently
    - Supports checkpointing for resumability
    """

    def __init__(
        self,
        steps: list[Step],
        checkpoint_store: Optional["CheckpointStore"] = None,
    ) -> None:
        self.steps = steps
        self.checkpoint_store = checkpoint_store
        self._validate_step_chain()

    def _validate_step_chain(self) -> None:
        """Validate that steps can be chained (provides feed into requires)."""
        available: set[str] = set()
        for i, step in enumerate(self.steps):
            missing = step.cap.missing_requirements(available)
            if missing and i > 0:
                # First step's requirements come from initial context
                prev_step = self.steps[i - 1]
                raise ContractViolationError(
                    f"Step {step.name!r} requires {missing} but previous step "
                    f"{prev_step.name!r} only provides {prev_step.cap.provides}"
                )
            available.update(step.cap.provides)

    def _check_preconditions(self, step: Step, ctx: Ctx) -> None:
        """Check that context satisfies step's preconditions."""
        ctx_keys = set(ctx.keys())
        missing = step.cap.missing_requirements(ctx_keys)
        if missing:
            raise ContractViolationError(
                f"Step {step.name!r} requires {missing} but context only has {ctx_keys}"
            )

    def _check_postconditions(self, step: Step, ctx: Ctx) -> None:
        """Check that step fulfilled its postconditions."""
        ctx_keys = set(ctx.keys())
        missing = step.cap.provides - ctx_keys
        if missing:
            raise ContractViolationError(
                f"Step {step.name!r} must provide {missing} but context only has {ctx_keys}"
            )

    async def _run_step(self, step: Step, ctx: Ctx) -> Ctx:
        """Run a step, handling both sync and async."""
        result = step.run(ctx)
        if inspect.isawaitable(result):
            result = await result
        return result

    async def run(self, path: str, checkpoint: Cursor | None = None) -> Ctx:
        """
        Run the pipeline on a document.

        Args:
            path: Path to the document
            checkpoint: Optional cursor to resume from

        Returns:
            Final context after all steps complete
        """
        # Initialize context
        ctx: Ctx = {"path": path}

        # Load checkpoint if available
        if checkpoint:
            ctx["checkpoint"] = checkpoint
        elif self.checkpoint_store:
            doc_id = path  # Use path as doc_id by default
            saved = self.checkpoint_store.load(doc_id)
            if saved:
                ctx["checkpoint"] = saved

        return await self.run_with_ctx(ctx)

    async def run_with_ctx(self, ctx: Ctx) -> Ctx:
        """Run the pipeline with an existing context."""
        for step in self.steps:
            self._check_preconditions(step, ctx)
            ctx = await self._run_step(step, ctx)
            self._check_postconditions(step, ctx)

        return ctx

    def run_sync(self, path: str, checkpoint: Cursor | None = None) -> Ctx:
        """Synchronous wrapper for run()."""
        return asyncio.run(self.run(path, checkpoint))

    def __repr__(self) -> str:
        step_names = [s.name for s in self.steps]
        return f"Pipeline(steps={step_names})"
