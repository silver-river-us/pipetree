"""Capability-based contract system."""

from pipetree.domain.capability.capability import Capability
from pipetree.domain.capability.predefined import (
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
