"""File-based progress notifier with CSV output."""

import csv
from pathlib import Path
from typing import IO

from pipetree.infrastructure.progress.progress_notifier import (
    ProgressEvent,
    ProgressNotifier,
)


class FileProgressNotifier(ProgressNotifier):
    """
    Writes progress events to a CSV file.

    Flushes after each write for real-time streaming.
    """

    FIELDNAMES = [
        "timestamp",
        "step_name",
        "step_index",
        "total_steps",
        "event_type",
        "duration_s",
        "error",
        "current",
        "total",
        "message",
    ]

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._file: IO[str] | None = None
        self._writer: csv.DictWriter[str] | None = None
        self._open()

    def _open(self) -> None:
        """Open file and write header."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(self.path, "w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=self.FIELDNAMES)
        self._writer.writeheader()
        self._file.flush()

    def notify(self, event: ProgressEvent) -> None:
        """Write event to CSV file."""
        if self._writer is None or self._file is None:
            return

        row = {
            "timestamp": event.timestamp,
            "step_name": event.step_name,
            "step_index": event.step_index,
            "total_steps": event.total_steps,
            "event_type": event.event_type,
            "duration_s": event.duration_s if event.duration_s is not None else "",
            "error": event.error if event.error is not None else "",
            "current": event.current if event.current is not None else "",
            "total": event.total if event.total is not None else "",
            "message": event.message if event.message is not None else "",
        }
        self._writer.writerow(row)
        self._file.flush()

    def close(self) -> None:
        """Close the file."""
        if self._file is not None:
            self._file.close()
            self._file = None
            self._writer = None
