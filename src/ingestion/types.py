"""Backward-compatible re-exports from domain.types."""

from ingestion.domain.types import (
    Chunk,
    ConcurrencyConfig,
    Ctx,
    Cursor,
    VecBatch,
    VecRecord,
)

__all__ = [
    "Chunk",
    "ConcurrencyConfig",
    "Ctx",
    "Cursor",
    "VecBatch",
    "VecRecord",
]
