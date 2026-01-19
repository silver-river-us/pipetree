"""Pipeline orchestrator with contract validation."""

import asyncio
import inspect
import time
import tracemalloc
from typing import TYPE_CHECKING, TypeVar

from pipetree.domain.pipeline.contract_violation_error import ContractViolationError
from pipetree.domain.step.step import Step
from pipetree.domain.types.context import Context

if TYPE_CHECKING:
    from pipetree.infrastructure.progress import ProgressNotifier

# TypeVar for preserving context type through the pipeline
CtxT = TypeVar("CtxT", bound=Context)


def _generate_run_id() -> str:
    """Generate a unique run ID."""
    import uuid

    return str(uuid.uuid4())


class Pipetree:
    """
    Pipeline orchestrator that runs steps sequentially with contract validation.

    Features:
    - Validates preconditions before each step
    - Validates postconditions after each step
    - Supports both sync and async steps transparently
    - Optional progress notification
    """

    def __init__(
        self,
        steps: list[Step],
        progress_notifier: "ProgressNotifier | None" = None,
        name: str = "Pipeline",
    ) -> None:
        self.steps = steps
        self.name = name
        self._notifier = progress_notifier
        self._run_id: str | None = None
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
            # First step's requirements are assumed to come from initial context
            if i == 0:
                available.update(step.cap.requires)
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

    @property
    def run_id(self) -> str | None:
        """Get the current run ID."""
        return self._run_id

    def _register_run(self) -> None:
        """Register this run with the notifier if it supports it."""
        if self._notifier is None:
            return

        # Check if notifier supports run registration (SQLiteProgressNotifier)
        if hasattr(self._notifier, "register_run"):
            step_names = [s.name for s in self.steps]
            self._run_id = self._notifier.register_run(self.name, step_names)
        elif hasattr(self._notifier, "run_id"):
            self._run_id = self._notifier.run_id

    def _complete_run(self, status: str = "completed") -> None:
        """Mark the run as completed if the notifier supports it."""
        if self._notifier is None:
            return

        if hasattr(self._notifier, "complete_run"):
            self._notifier.complete_run(status)

    async def run(self, ctx: CtxT) -> CtxT:
        """
        Run the pipeline with the given context.

        Args:
            ctx: The context object with initial data

        Returns:
            The same context object after all steps complete
        """
        total_steps = len(self.steps)

        # Register run with notifier (for SQLite, this pre-creates all steps)
        self._register_run()

        # Inject notifier into context for sub-step progress reporting
        ctx._notifier = self._notifier
        ctx._total_steps = total_steps

        # Start memory tracking
        tracemalloc.start()

        for i, step in enumerate(self.steps):
            # Update context with current step info
            ctx._step_name = step.name
            ctx._step_index = i

            # Notify step started
            if self._notifier:
                self._notifier.step_started(step.name, i, total_steps)

            # Reset peak memory counter before step
            tracemalloc.reset_peak()
            start_time = time.perf_counter()

            try:
                self._check_preconditions(step, ctx)
                ctx = await self._run_step(step, ctx)
                self._check_postconditions(step, ctx)

                # Get peak memory for this step (in MB)
                _, peak_bytes = tracemalloc.get_traced_memory()
                peak_mem_mb = peak_bytes / (1024 * 1024)

                # Notify step completed
                duration = time.perf_counter() - start_time
                if self._notifier:
                    self._notifier.step_completed(
                        step.name, i, total_steps, duration, peak_mem_mb
                    )

            except Exception as e:
                # Notify step failed
                duration = time.perf_counter() - start_time
                if self._notifier:
                    self._notifier.step_failed(
                        step.name, i, total_steps, duration, str(e)
                    )
                self._complete_run("failed")
                tracemalloc.stop()
                raise

        tracemalloc.stop()
        self._complete_run("completed")
        return ctx

    def run_sync(self, ctx: CtxT) -> CtxT:
        """Synchronous wrapper for run()."""
        return asyncio.run(self.run(ctx))

    def __repr__(self) -> str:
        step_names = [s.name for s in self.steps]
        return f"Pipetree(steps={step_names})"
