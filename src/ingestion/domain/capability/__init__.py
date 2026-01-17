"""Capability-based contract system."""

from ingestion.domain.capability.capability import Capability
from ingestion.domain.capability.predefined import (
    CHUNKING,
    CLASSIFICATION,
    EMBEDDING,
    INDEX_WRITING,
    PAGE_ITERATION,
    TEXT_EXTRACTION,
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
