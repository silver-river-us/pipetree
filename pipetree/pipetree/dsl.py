"""
DSL for defining pipelines with minimal syntax.

Example usage:

    from pipetree.dsl import step, branch, route, pipeline

    @step(requires={"path"}, provides={"pdf"})
    class LoadPdf(Step):
        def run(self, ctx): ...

    @step(requires={"texts", "category"}, provides={"processed_ops"})
    @branch("ops")
    class ProcessOps(Step):
        def run(self, ctx): ...

    # Clean pipeline definition
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

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypeVar

from pipetree.domain.capability.capability import Capability
from pipetree.domain.pipeline.pipeline import Pipetree
from pipetree.domain.step.router import Router
from pipetree.domain.step.step import Step
from pipetree.domain.types.context import Context

if TYPE_CHECKING:
    from pipetree.infrastructure.progress import ProgressNotifier

T = TypeVar("T", bound=type[Step])


# =============================================================================
# Decorators
# =============================================================================


def step(
    requires: set[str] | None = None,
    provides: set[str] | None = None,
    name: str | None = None,
) -> Any:
    """
    Decorator to define a step with its capability inline.

    Usage:
        @step(requires={"path"}, provides={"pdf"})
        class LoadPdf(Step):
            def run(self, ctx): ...

    The capability name defaults to the snake_case version of the class name.
    """

    def decorator(cls: T) -> T:
        # Derive name from class name if not provided
        cap_name = name or _to_snake_case(cls.__name__)

        # Store capability info on the class
        cls._dsl_capability = Capability(
            name=cap_name,
            requires=requires or set(),
            provides=provides or set(),
        )
        cls._dsl_name = cap_name

        return cls

    return decorator


def branch(branch_key: str) -> Any:
    """
    Decorator to mark which branch a step handles.

    Usage:
        @step(requires={"texts"}, provides={"processed_ops"})
        @branch("ops")
        class ProcessOps(Step):
            def run(self, ctx): ...
    """

    def decorator(cls: T) -> T:
        cls._dsl_branch = branch_key
        return cls

    return decorator


# =============================================================================
# Route marker
# =============================================================================


@dataclass
class BranchTarget:
    """
    A branch key pointing to a target step or nested route.

    Created by: ops >> process_ops
    Or: parts >> parts_type >> [...]
    """

    key: str
    target: Any = None

    def __rshift__(self, target: Any) -> BranchTarget:
        """
        Allow: ops >> step or ops >> route >> [...]

        Handle chaining like: B("parts") >> parts_type >> [...]
        where parts_type is a RouteMarker.
        """
        if isinstance(self.target, RouteMarker) and isinstance(target, list):
            # Chained: B("parts") >> parts_type >> [branches]
            # Apply branches to the existing RouteMarker
            filled_route = RouteMarker(
                key=self.target.key,
                branches=target,
                default=self.target.default,
            )
            return BranchTarget(key=self.key, target=filled_route)
        return BranchTarget(key=self.key, target=target)

    def __repr__(self) -> str:
        return f"{self.key} >> {self.target!r}"


def B(key: str) -> BranchTarget:
    """
    Create a branch marker for explicit branch assignment.

    Usage:
        category >> [
            B("ops") >> process_ops,
            B("parts") >> parts_type >> [...],
        ]

    Short for "Branch" - keeps the DSL concise.
    """
    return BranchTarget(key=key)


@dataclass
class RouteMarker:
    """
    Marker for defining routes in the DSL.

    Created by using >> on a route key:
        category >> [step1, step2]
    """

    key: str
    branches: list[Any] = field(default_factory=list)
    default: str | None = None

    def __rshift__(self, branches: list[Any] | BranchTarget) -> RouteMarker | BranchTarget:
        """
        Allow:
            category >> [step1, step2]
            parts >> parts_type >> [...]  (chained routes)
        """
        if isinstance(branches, list):
            return RouteMarker(key=self.key, branches=branches, default=self.default)
        # Chained route: this route becomes a branch target
        return BranchTarget(key=self.key, target=branches)

    def __repr__(self) -> str:
        return f"route({self.key!r})"


def route(key: str, default: str | None = None) -> RouteMarker:
    """
    Create a route marker for the DSL.

    Usage:
        route("category") >> [process_ops, process_parts]

    Or use a pre-defined route variable:
        category = route("category")
        category >> [process_ops, process_parts]
    """
    return RouteMarker(key=key, default=default)


# =============================================================================
# Pipeline builder
# =============================================================================


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


# =============================================================================
# Internal helpers
# =============================================================================


def _to_snake_case(name: str) -> str:
    """Convert CamelCase to snake_case."""
    result = []
    for i, char in enumerate(name):
        if char.isupper() and i > 0:
            result.append("_")
        result.append(char.lower())
    return "".join(result)


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

        return step_or_class(cap=cap, name=name)

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
            branch_key = _get_branch_key(branch_item)

            if branch_key is None:
                raise ValueError(
                    f"Step {step.name} used in route({marker.key!r}) must have "
                    f"@branch decorator to specify which branch it handles"
                )

            table[branch_key] = step
            branch_outputs[branch_key] = list(step.cap.provides)

    # Build capability for the router
    # Requires: the routing key + union of all branch requires
    # Provides: union of all branch provides
    all_requires: set[str] = {marker.key}
    all_provides: set[str] = set()

    for branch_key, target in table.items():
        if isinstance(target, Router):
            all_requires.update(target.cap.requires)
            all_provides.update(target.cap.provides)
        else:
            all_requires.update(target.cap.requires)
            all_provides.update(target.cap.provides)

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
                    f"Context attribute {self._route_key!r} is not set. "
                    f"Cannot route."
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


# =============================================================================
# Convenience: pre-defined route markers for common patterns
# =============================================================================

# Users can create their own:
#   category = route("category")
#   parts_type = route("parts_type")
#
# Then use in pipeline:
#   category >> [process_ops, parts_type >> [process_mechanical, process_electrical]]
