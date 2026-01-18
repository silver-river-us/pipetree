"""Text chunk with metadata."""

from typing import Any, TypedDict

from pipetree.domain.types.cursor import Cursor


class Chunk(TypedDict):
    """A text chunk with metadata."""

    id: str
    text: str
    meta: dict[str, Any]
    cursor: Cursor
