"""Checkpoint cursor for resumability."""

from typing import Any, TypedDict


class Cursor(TypedDict, total=False):
    """Checkpoint cursor for resumability."""

    page: int
    chunk_idx: int
    extra: dict[str, Any]
