"""Backward-compatible re-exports from domain.capability."""

from ingestion.domain.capability import (
    CHUNKING,
    CLASSIFICATION,
    EMBEDDING,
    INDEX_WRITING,
    PAGE_ITERATION,
    TEXT_EXTRACTION,
    Capability,
)

__all__ = [
    "CHUNKING",
    "CLASSIFICATION",
    "EMBEDDING",
    "INDEX_WRITING",
    "PAGE_ITERATION",
    "TEXT_EXTRACTION",
    "Capability",
]
