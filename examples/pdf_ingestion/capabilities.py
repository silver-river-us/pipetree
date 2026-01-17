"""Capability definitions for the PDF ingestion pipeline."""

from pipetree import Capability

LOAD_PDF = Capability(
    name="load_pdf",
    requires={"path"},
    provides={"pdf", "total_pages"},
)

TEXT_EXTRACTION = Capability(
    name="text_extraction",
    requires={"pdf", "num_cores"},
    provides={"texts"},
)

SAVE_TEXT = Capability(
    name="save_text",
    requires={"texts", "output_path"},
    provides={"saved"},
)
