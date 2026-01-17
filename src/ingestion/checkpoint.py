"""Backward-compatible re-exports from infrastructure.checkpoint."""

from ingestion.infrastructure.checkpoint import (
    CheckpointStore,
    FileCheckpointStore,
    InMemoryCheckpointStore,
)

__all__ = [
    "CheckpointStore",
    "FileCheckpointStore",
    "InMemoryCheckpointStore",
]
