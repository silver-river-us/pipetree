"""Pipeline context - the streaming data bus."""

from collections.abc import AsyncIterator, Iterator
from typing import Any, TypedDict

from ingestion.domain.types.chunk import Chunk
from ingestion.domain.types.cursor import Cursor
from ingestion.domain.types.vec_record import VecBatch


class Ctx(TypedDict, total=False):
    """
    Context passed through the pipeline - acts as a streaming data bus.

    For large documents, values are streams/iterators, not full materializations.
    """

    path: str
    pdf: Any
    doc_id: str
    kind: str  # "ops" | "parts" | ...
    scanned: bool
    language: str
    checkpoint: Cursor
    pages: Iterator[Any] | AsyncIterator[Any]
    texts: Iterator[tuple[int, str]] | AsyncIterator[tuple[int, str]]
    chunks: Iterator[Chunk] | AsyncIterator[Chunk]
    vec_batches: AsyncIterator[VecBatch]
    done: bool
