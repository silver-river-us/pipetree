"""Backward-compatible re-exports from infrastructure.registry."""

from ingestion.infrastructure.registry import (
    Registry,
    StepFactory,
    global_registry,
    register,
)

__all__ = [
    "Registry",
    "StepFactory",
    "global_registry",
    "register",
]
