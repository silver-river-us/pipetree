"""Backward-compatible re-exports from domain.pipeline."""

from ingestion.domain.pipeline import (
    ContractViolationError,
    Pipeline,
)

__all__ = [
    "ContractViolationError",
    "Pipeline",
]
