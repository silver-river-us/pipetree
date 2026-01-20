"""Pipeline builder for the DSL."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pipetree.domain.capability.capability import Capability
from pipetree.domain.pipeline.pipeline import Pipetree
from pipetree.domain.step.router import Router
from pipetree.domain.step.step import Step
from pipetree.domain.types.context import Context

from .markers import BranchTarget, RouteMarker

if TYPE_CHECKING:
    from pipetree.infrastructure.progress import ProgressNotifier


def pipeline(
    name: str,
    steps: list[Any],
    progress_notifier: ProgressNotifier | None = None,
) -> Pipetree:
    """
    Build a pipeline from the DSL definition.

    Usage:
        pdf_pipeline = pipeline("PDF Pipeline", [
            load_pdf,
            extract_text,
            categorize,
            category >> [
                process_ops,
                parts_type >> [
                    process_mechanical,
                    process_electrical,
                ],
            ],
            save_text,
        ])
    """
    built_steps = _build_steps(steps)
    return Pipetree(steps=built_steps, progress_notifier=progress_notifier, name=name)


def _get_branch_key(step_or_class: Any) -> str | None:
    """Get the branch key from a step instance or class."""
    if isinstance(step_or_class, Step):
        return getattr(step_or_class.__class__, "_dsl_branch", None)
    return getattr(step_or_class, "_dsl_branch", None)


def _instantiate_step(step_or_class: Any) -> Step:
    """
    Convert a step class or instance to a Step instance.

    Handles:
    - Step instances (returned as-is)
    - Step classes with @step decorator (instantiated with derived capability)
    - Step classes without decorator (error)
    """
    # Already an instance
    if isinstance(step_or_class, Step):
        return step_or_class

    # Class with @step decorator
    if isinstance(step_or_class, type) and issubclass(step_or_class, Step):
        cap = getattr(step_or_class, "_dsl_capability", None)
        name = getattr(step_or_class, "_dsl_name", None)

        if cap is None:
            raise ValueError(
                f"Step class {step_or_class.__name__} must use @step decorator "
                "or be instantiated with a Capability"
            )

        return step_or_class(cap=cap, name=name or cap.name)

    raise TypeError(
        f"Expected Step class or instance, got {type(step_or_class).__name__}"
    )


def _build_steps(items: list[Any]) -> list[Step]:
    """
    Build a list of Step instances from DSL items.

    Handles:
    - Step classes/instances
    - RouteMarker (converted to auto-generated Router)
    """
    result: list[Step] = []

    for item in items:
        if isinstance(item, RouteMarker):
            router = _build_router(item)
            result.append(router)
        else:
            result.append(_instantiate_step(item))

    return result


def _build_router(marker: RouteMarker) -> Router:
    """
    Build a Router from a RouteMarker.

    The router's pick() method reads the context attribute named by marker.key.
    """
    # Build the routing table
    table: dict[str, Step | Pipetree] = {}
    branch_outputs: dict[str, list[str]] = {}

    for branch_item in marker.branches:
        if isinstance(branch_item, BranchTarget):
            # Explicit branch assignment: B("ops") >> step or ops >> step
            branch_key = branch_item.key
            target = branch_item.target

            if isinstance(target, RouteMarker):
                # Nested route: parts >> parts_type >> [...]
                nested_router = _build_router(target)
                table[branch_key] = nested_router
                branch_outputs[branch_key] = list(nested_router.cap.provides)
            elif isinstance(target, BranchTarget):
                # Chained: B("parts") >> parts_type >> [...] where parts_type >> [...] is a BranchTarget
                # Unwrap the chain
                inner = target
                while isinstance(inner.target, BranchTarget):
                    inner = inner.target
                if isinstance(inner.target, RouteMarker):
                    nested_router = _build_router(inner.target)
                    table[branch_key] = nested_router
                    branch_outputs[branch_key] = list(nested_router.cap.provides)
                else:
                    step = _instantiate_step(inner.target)
                    table[branch_key] = step
                    branch_outputs[branch_key] = list(step.cap.provides)
            else:
                # Direct step: ops >> process_ops
                step = _instantiate_step(target)
                table[branch_key] = step
                branch_outputs[branch_key] = list(step.cap.provides)

        elif isinstance(branch_item, RouteMarker):
            # Nested route without explicit branch key - use route key as branch
            nested_router = _build_router(branch_item)
            branch_key = branch_item.key
            table[branch_key] = nested_router
            branch_outputs[branch_key] = list(nested_router.cap.provides)
        else:
            # Regular step - get branch key from @branch decorator
            step = _instantiate_step(branch_item)
            inferred_branch_key = _get_branch_key(branch_item)

            if inferred_branch_key is None:
                raise ValueError(
                    f"Step {step.name} used in route({marker.key!r}) must have "
                    f"@branch decorator to specify which branch it handles"
                )

            table[inferred_branch_key] = step
            branch_outputs[inferred_branch_key] = list(step.cap.provides)

    # Build capability for the router
    # Requires: the routing key + union of all branch requires
    # Provides: union of all branch provides
    all_requires: set[str] = {marker.key}
    all_provides: set[str] = set()

    for target in table.values():
        if isinstance(target, (Step, Router)):
            all_requires.update(target.cap.requires)
            all_provides.update(target.cap.provides)
        elif isinstance(
            target, Pipetree
        ):  # pragma: no cover (defensive - DSL builder doesn't add Pipetree to table)
            # Pipetree has steps, get capability from first/last step
            if target.steps:
                all_requires.update(target.steps[0].cap.requires)
                all_provides.update(target.steps[-1].cap.provides)

    router_cap = Capability(
        name=f"route_{marker.key}",
        requires=all_requires,
        provides=all_provides,
    )

    # Create a dynamic Router subclass with the pick method
    class DynamicRouter(Router):
        _route_key = marker.key

        def pick(self, ctx: Context) -> str:
            value = getattr(ctx, self._route_key, None)
            if value is None:
                raise ValueError(
                    f"Context attribute {self._route_key!r} is not set. Cannot route."
                )
            return str(value)

    # Set branch_outputs as class variable
    DynamicRouter.branch_outputs = branch_outputs

    return DynamicRouter(
        cap=router_cap,
        name=f"route_{marker.key}",
        table=table,
        default=marker.default,
    )
