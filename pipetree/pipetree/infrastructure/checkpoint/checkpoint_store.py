"""Abstract checkpoint store interface."""

from abc import ABC, abstractmethod

from pipetree.domain.types.cursor import Cursor


class CheckpointStore(ABC):
    """Abstract base class for checkpoint storage."""

    @abstractmethod
    def load(self, doc_id: str) -> Cursor | None:
        """Load checkpoint for a document."""
        ...

    @abstractmethod
    def save(self, doc_id: str, cursor: Cursor) -> None:
        """Save checkpoint for a document."""
        ...

    @abstractmethod
    def delete(self, doc_id: str) -> None:
        """Delete checkpoint for a document."""
        ...
