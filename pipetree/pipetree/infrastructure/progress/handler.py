"""Progress handler protocol and implementations."""

import sys
from typing import Protocol


class ProgressHandler(Protocol):
    """Protocol for handling progress events."""

    def on_started(self, step_name: str) -> None:
        """Called when a step starts."""
        ...

    def on_completed(self, step_name: str, duration_s: float | None) -> None:
        """Called when a step completes."""
        ...

    def on_failed(self, step_name: str, error: str) -> None:
        """Called when a step fails."""
        ...

    def on_progress(
        self, step_name: str, current: int, total: int, message: str | None
    ) -> None:
        """Called when progress is reported."""
        ...

    def on_cleanup(self) -> None:
        """Called when the watcher is stopping."""
        ...


class ConsoleProgressHandler:
    """Handler that prints progress to console with progress bars."""

    def __init__(self) -> None:
        self._last_progress_line = ""

    def _clear_progress_line(self) -> None:
        """Clear the current progress line if any."""
        if self._last_progress_line:
            sys.stdout.write("\r" + " " * len(self._last_progress_line) + "\r")
            self._last_progress_line = ""

    def on_started(self, step_name: str) -> None:
        """Print step started message."""
        self._clear_progress_line()
        print(f"[{step_name}] Started")

    def on_completed(self, step_name: str, duration_s: float | None) -> None:
        """Print step completed message."""
        self._clear_progress_line()
        if duration_s:
            print(f"[{step_name}] Completed in {duration_s:.2f}s")
        else:
            print(f"[{step_name}] Completed")

    def on_failed(self, step_name: str, error: str) -> None:
        """Print step failed message."""
        self._clear_progress_line()
        print(f"[{step_name}] FAILED: {error}")

    def on_progress(
        self, step_name: str, current: int, total: int, message: str | None
    ) -> None:
        """Print progress bar."""
        if total > 0:
            pct = current / total * 100
            bar_width = 30
            filled = int(bar_width * current / total)
            bar = "=" * filled + "-" * (bar_width - filled)

            progress_line = f"[{step_name}] [{bar}] {pct:5.1f}% ({current}/{total})"
            if message:
                progress_line += f" {message}"

            sys.stdout.write("\r" + progress_line)
            sys.stdout.flush()
            self._last_progress_line = progress_line

    def on_cleanup(self) -> None:
        """Clear any remaining progress line."""
        self._clear_progress_line()
        sys.stdout.flush()
