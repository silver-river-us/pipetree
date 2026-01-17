"""Capability definitions for the PDF ingestion pipeline."""

from pipetree import Capability

LOAD_PDF = Capability(
    name="load_pdf",
    requires={"path"},
    provides={"pdf"},
)

PAGE_EXTRACTION = Capability(
    name="page_extraction",
    requires={"pdf"},
    provides={"pages"},
)

TEXT_EXTRACTION = Capability(
    name="text_extraction",
    requires={"pages"},
    provides={"texts"},
)

CHUNKING = Capability(
    name="chunking",
    requires={"texts"},
    provides={"chunks"},
)
