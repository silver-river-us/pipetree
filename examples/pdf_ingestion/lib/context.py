"""Typed context for the PDF ingestion pipeline."""

import json
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO

from pipetree import Context


class LazyTextFile:
    """
    File-backed text storage for memory-efficient streaming.

    Stores texts as JSON lines (one per page) to avoid loading all into memory.
    Supports iteration, indexing, and length without full memory load.
    """

    _temp: IO[str] | None
    _path: Path
    _owns_file: bool
    _count: int
    _finalized: bool

    def __init__(self, path: Path | None = None):
        if path is None:
            # Create temp file that persists until explicitly closed
            # (intentionally not using context manager - file must persist)
            self._temp = tempfile.NamedTemporaryFile(  # noqa: SIM115
                mode="w+", suffix=".jsonl", delete=False
            )
            self._path = Path(self._temp.name)
            self._owns_file = True
        else:
            self._path = path
            self._temp = None
            self._owns_file = False
        self._count = 0
        self._finalized = False

    @property
    def path(self) -> Path:
        return self._path

    def append(self, text: str) -> None:
        """Append a page's text to the file."""
        if self._finalized:
            raise RuntimeError("Cannot append to finalized LazyTextFile")
        with open(self._path, "a") as f:
            f.write(json.dumps(text) + "\n")
        self._count += 1

    def finalize(self) -> None:
        """Mark as complete - no more writes allowed."""
        self._finalized = True

    def __len__(self) -> int:
        return self._count

    def __iter__(self) -> Iterator[str]:
        """Iterate through texts without loading all into memory."""
        with open(self._path) as f:
            for line in f:
                yield json.loads(line.strip())

    def __getitem__(self, idx: int) -> str:
        """Get a specific page's text (loads one line at a time)."""
        if idx < 0:
            idx = self._count + idx
        with open(self._path) as f:
            for i, line in enumerate(f):
                if i == idx:
                    return json.loads(line.strip())
        raise IndexError(f"Index {idx} out of range")

    def join(self, separator: str = " ") -> str:
        """Join all texts with separator (streams through file)."""
        return separator.join(self)

    def to_list(self) -> list[str]:
        """Convert to list (loads all into memory - use sparingly)."""
        return list(self)

    def cleanup(self) -> None:
        """Delete the backing file."""
        if self._owns_file and self._path.exists():
            self._path.unlink()


@dataclass
class PdfContext(Context):
    """Context for PDF ingestion pipeline with typed attributes."""

    # Initial input
    path: str
    output_path: str | None = None

    # After LoadPdfStep - marks PDF as validated, page count extracted
    pdf: bool = False
    total_pages: int = 0

    # After ExtractTextStep - file-backed streaming texts (memory efficient)
    # Use texts.append() to add, iterate with `for text in ctx.texts`
    _texts_file: LazyTextFile | None = field(default=None, repr=False)

    # After CategorizeStep - category of the document
    category: str | None = None  # "ops" or "parts"
    parts_type: str | None = None  # "mechanical" or "electrical" (for parts docs)

    # After branch-specific processing
    processed_ops: dict | None = None
    processed_parts: dict | None = None

    # After nested branch processing (parts -> mechanical/electrical)
    processed_mechanical: dict | None = None
    processed_electrical: dict | None = None

    # After SaveTextStep
    saved: bool = False

    @property
    def texts(self) -> LazyTextFile:
        """Get the file-backed text storage (creates on first access)."""
        if self._texts_file is None:
            self._texts_file = LazyTextFile()
        return self._texts_file

    @texts.setter
    def texts(self, value: list[str] | LazyTextFile) -> None:
        """Set texts - accepts list for backwards compatibility."""
        if isinstance(value, LazyTextFile):
            self._texts_file = value
        elif isinstance(value, list):
            # Convert list to file-backed storage
            self._texts_file = LazyTextFile()
            for text in value:
                self._texts_file.append(text)
            self._texts_file.finalize()
        else:
            raise TypeError(f"Expected list or LazyTextFile, got {type(value)}")

    def keys(self) -> set[str]:
        """Override to include 'texts' property in capability checking."""
        result = super().keys()
        # Include 'texts' if the file-backed storage has been initialized
        if self._texts_file is not None:
            result.add("texts")
        return result
