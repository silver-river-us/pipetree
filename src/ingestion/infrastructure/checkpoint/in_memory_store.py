"""In-memory checkpoint store implementation."""

from ingestion.domain.types.cursor import Cursor
from ingestion.infrastructure.checkpoint.checkpoint_store import CheckpointStore


class InMemoryCheckpointStore(CheckpointStore):
    """In-memory checkpoint store for testing."""

    def __init__(self) -> None:
        self._store: dict[str, Cursor] = {}

    def load(self, doc_id: str) -> Cursor | None:
        return self._store.get(doc_id)

    def save(self, doc_id: str, cursor: Cursor) -> None:
        self._store[doc_id] = cursor

    def delete(self, doc_id: str) -> None:
        self._store.pop(doc_id, None)

    def clear(self) -> None:
        """Clear all checkpoints."""
        self._store.clear()
