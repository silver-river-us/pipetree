"""Predefined capabilities for common pipeline steps."""

from pipetree.domain.capability.capability import Capability

PAGE_ITERATION = Capability(
    name="page_iteration",
    requires={"pdf"},
    provides={"pages"},
)

TEXT_EXTRACTION = Capability(
    name="text_extraction",
    requires={"pages", "scanned"},
    provides={"texts"},
)

CHUNKING = Capability(
    name="chunking",
    requires={"texts", "kind"},
    provides={"chunks"},
)

EMBEDDING = Capability(
    name="embedding",
    requires={"chunks"},
    provides={"vec_batches"},
)

INDEX_WRITING = Capability(
    name="index_writing",
    requires={"vec_batches", "doc_id"},
    provides={"done"},
)

CLASSIFICATION = Capability(
    name="classification",
    requires={"pdf"},
    provides={"kind", "scanned"},
)
