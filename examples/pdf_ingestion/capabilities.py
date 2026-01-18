"""Capability definitions for the PDF ingestion pipeline."""

from pipetree import Capability

LOAD_PDF = Capability(
    name="load_pdf",
    requires={"path", "output_path"},
    provides={"pdf", "total_pages"},
)

TEXT_EXTRACTION = Capability(
    name="text_extraction",
    requires={"pdf"},
    provides={"texts"},
)

# Categorization - determines if document is ops or parts manual
CATEGORIZE = Capability(
    name="categorize",
    requires={"texts"},
    provides={"category"},
)

# Branch-specific processing
PROCESS_OPS = Capability(
    name="process_ops",
    requires={"texts", "category"},
    provides={"processed_ops"},
)

PROCESS_PARTS = Capability(
    name="process_parts",
    requires={"texts", "category"},
    provides={"processed_parts"},
)

# Nested branch processing for parts (mechanical vs electrical)
PROCESS_MECHANICAL = Capability(
    name="process_mechanical",
    requires={"texts", "category"},
    provides={"processed_mechanical"},
)

PROCESS_ELECTRICAL = Capability(
    name="process_electrical",
    requires={"texts", "category"},
    provides={"processed_electrical"},
)

SAVE_TEXT = Capability(
    name="save_text",
    requires={"texts", "output_path"},
    provides={"saved"},
)
