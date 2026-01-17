"""Typed context for the PDF ingestion pipeline."""

from dataclasses import dataclass, field

from pipetree import Context


@dataclass
class PdfContext(Context):
    """Context for PDF ingestion pipeline with typed attributes."""

    # Initial input
    path: str
    output_path: str | None = None

    # Configuration
    num_cores: int = 1

    # After LoadPdfStep - marks PDF as validated, page count extracted
    pdf: bool = False
    total_pages: int = 0

    # After ExtractTextStep (parallel) - pages extracted one by one
    texts: list[str] = field(default_factory=list)

    # After SaveTextStep
    saved: bool = False
