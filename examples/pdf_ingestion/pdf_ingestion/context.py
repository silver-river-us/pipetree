"""Typed context for the PDF ingestion pipeline."""

from dataclasses import dataclass, field

from pipetree import Context


@dataclass
class PdfContext(Context):
    """Context for PDF ingestion pipeline with typed attributes."""

    # Initial input
    path: str
    output_path: str | None = None

    # After LoadPdfStep - marks PDF as validated, page count extracted
    pdf: bool = False
    total_pages: int = 0

    # After ExtractTextStep (parallel) - pages extracted one by one
    texts: list[str] = field(default_factory=list)

    # After CategorizeStep - category of the document
    category: str | None = None  # "ops" or "parts"

    # After branch-specific processing
    processed_ops: dict | None = None
    processed_parts: dict | None = None

    # After nested branch processing (parts -> mechanical/electrical)
    processed_mechanical: dict | None = None
    processed_electrical: dict | None = None

    # After SaveTextStep
    saved: bool = False
