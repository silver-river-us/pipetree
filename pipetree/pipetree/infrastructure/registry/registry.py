"""Registry for step factories and swappable implementations."""

from collections.abc import Callable
from typing import Any

from pipetree.domain.step.step import Step

# Type alias for step factories
StepFactory = Callable[..., Step]


class Registry:
    """
    Registry for step implementations.

    Allows registering multiple implementations for each capability,
    enabling experimentation and A/B testing.
    """

    def __init__(self) -> None:
        self._registry: dict[str, dict[str, StepFactory]] = {}

    def register(
        self,
        cap_name: str,
        impl_name: str,
        factory: StepFactory,
    ) -> None:
        """Register a step factory for a capability."""
        if cap_name not in self._registry:
            self._registry[cap_name] = {}
        self._registry[cap_name][impl_name] = factory

    def unregister(self, cap_name: str, impl_name: str) -> None:
        """Unregister a step factory."""
        if cap_name in self._registry:
            self._registry[cap_name].pop(impl_name, None)

    def list_capabilities(self) -> list[str]:
        """List all registered capabilities."""
        return list(self._registry.keys())

    def list_impls(self, cap_name: str) -> list[str]:
        """List all implementations for a capability."""
        return list(self._registry.get(cap_name, {}).keys())

    def get_factory(self, cap_name: str, impl_name: str) -> StepFactory:
        """Get a step factory."""
        if cap_name not in self._registry:
            raise KeyError(f"Unknown capability: {cap_name}")
        if impl_name not in self._registry[cap_name]:
            raise KeyError(
                f"Unknown implementation {impl_name!r} for capability {cap_name!r}. "
                f"Available: {self.list_impls(cap_name)}"
            )
        return self._registry[cap_name][impl_name]

    def make(self, cap_name: str, impl_name: str, **kwargs: Any) -> Step:
        """Create a step instance from a registered factory."""
        factory = self.get_factory(cap_name, impl_name)
        return factory(**kwargs)

    def decorator(
        self,
        cap_name: str,
        impl_name: str,
    ) -> Callable[[StepFactory], StepFactory]:
        """Decorator for registering step factories."""

        def wrapper(factory: StepFactory) -> StepFactory:
            self.register(cap_name, impl_name, factory)
            return factory

        return wrapper
