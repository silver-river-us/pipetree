"""Typed context for the PDF ingestion pipeline."""

from dataclasses import dataclass, field
from typing import Any

from pipetree import Context


@dataclass
class PdfContext(Context):
    """Context for PDF ingestion pipeline with typed attributes."""

    # Initial input
    path: str

    # After LoadPdfStep
    pdf: dict[str, Any] | None = None

    # After ExtractPagesStep
    pages: list[dict[str, Any]] = field(default_factory=list)

    # After ExtractTextStep
    texts: list[str] = field(default_factory=list)

    # After ChunkTextStep
    chunks: list[dict[str, Any]] = field(default_factory=list)
