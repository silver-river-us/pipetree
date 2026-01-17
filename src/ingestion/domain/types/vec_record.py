"""Vector record types for indexing."""

from typing import Any, TypedDict

from ingestion.domain.types.cursor import Cursor


class VecRecord(TypedDict):
    """A vector record ready for indexing."""

    id: str
    vec: Any
    meta: dict[str, Any]
    cursor: Cursor


VecBatch = list[VecRecord]
