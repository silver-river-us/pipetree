"""Pipeline orchestrator with contract validation."""

import asyncio
import inspect
from typing import TypeVar

from pipetree.domain.pipeline.contract_violation_error import ContractViolationError
from pipetree.domain.step.step import Step
from pipetree.domain.types.context import Context

# TypeVar for preserving context type through the pipeline
CtxT = TypeVar("CtxT", bound=Context)


class Pipetree:
    """
    Pipeline orchestrator that runs steps sequentially with contract validation.

    Features:
    - Validates preconditions before each step
    - Validates postconditions after each step
    - Supports both sync and async steps transparently
    """

    def __init__(self, steps: list[Step]) -> None:
        self.steps = steps
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

    def _check_preconditions(self, step: Step, ctx: Context) -> None:
        """Check that context satisfies step's preconditions."""
        ctx_keys = ctx.keys()
        missing = step.cap.missing_requirements(ctx_keys)
        if missing:
            raise ContractViolationError(
                f"Step {step.name!r} requires {missing} but context only has {ctx_keys}"
            )

    def _check_postconditions(self, step: Step, ctx: Context) -> None:
        """Check that step fulfilled its postconditions."""
        ctx_keys = ctx.keys()
        missing = step.cap.provides - ctx_keys
        if missing:
            raise ContractViolationError(
                f"Step {step.name!r} must provide {missing} but context only has {ctx_keys}"
            )

    async def _run_step(self, step: Step, ctx: CtxT) -> CtxT:
        """Run a step, handling both sync and async."""
        result = step.run(ctx)
        if inspect.isawaitable(result):
            result = await result
        return result  # type: ignore[return-value]

    async def run(self, ctx: CtxT) -> CtxT:
        """
        Run the pipeline with the given context.

        Args:
            ctx: The context object with initial data

        Returns:
            The same context object after all steps complete
        """
        for step in self.steps:
            self._check_preconditions(step, ctx)
            ctx = await self._run_step(step, ctx)
            self._check_postconditions(step, ctx)

        return ctx

    def run_sync(self, ctx: CtxT) -> CtxT:
        """Synchronous wrapper for run()."""
        return asyncio.run(self.run(ctx))

    def __repr__(self) -> str:
        step_names = [s.name for s in self.steps]
        return f"Pipetree(steps={step_names})"
