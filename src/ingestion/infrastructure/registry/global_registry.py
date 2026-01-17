"""Global registry instance and decorators."""

from collections.abc import Callable

from ingestion.infrastructure.registry.registry import Registry, StepFactory

# Global registry instance
global_registry = Registry()


def register(cap_name: str, impl_name: str) -> Callable[[StepFactory], StepFactory]:
    """Decorator for registering to global registry."""
    return global_registry.decorator(cap_name, impl_name)
