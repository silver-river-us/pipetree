"""File-based checkpoint store implementation."""

import json
from pathlib import Path
from typing import Any, cast

from ingestion.domain.types.cursor import Cursor
from ingestion.infrastructure.checkpoint.checkpoint_store import CheckpointStore


class FileCheckpointStore(CheckpointStore):
    """File-based checkpoint store."""

    def __init__(self, directory: Path | str) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path_for(self, doc_id: str) -> Path:
        # Sanitize doc_id for filesystem
        safe_id = doc_id.replace("/", "_").replace("\\", "_")
        return self.directory / f"{safe_id}.checkpoint.json"

    def load(self, doc_id: str) -> Cursor | None:
        path = self._path_for(doc_id)
        if not path.exists():
            return None
        try:
            data: Any = json.loads(path.read_text())
            return cast(Cursor, data)
        except (json.JSONDecodeError, OSError):
            return None

    def save(self, doc_id: str, cursor: Cursor) -> None:
        path = self._path_for(doc_id)
        path.write_text(json.dumps(cursor))

    def delete(self, doc_id: str) -> None:
        path = self._path_for(doc_id)
        if path.exists():
            path.unlink()
