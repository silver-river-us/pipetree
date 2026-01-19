"""Progress notifier interface and event data structure."""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ProgressEvent:
    """A progress event emitted during pipeline execution."""

    timestamp: float
    step_name: str
    step_index: int
    total_steps: int
    event_type: str  # "started" | "completed" | "failed" | "progress"
    duration_s: float | None = None
    peak_mem_mb: float | None = None
    error: str | None = None
    current: int | None = None
    total: int | None = None
    message: str | None = None


class ProgressNotifier(ABC):
    """Abstract base class for progress notification."""

    @abstractmethod
    def notify(self, event: ProgressEvent) -> None:
        """Emit a progress event."""
        ...

    def close(self) -> None:  # noqa: B027
        """Cleanup resources. Override if needed."""

    def step_started(self, step_name: str, step_index: int, total_steps: int) -> None:
        """Convenience method for step started events."""
        self.notify(
            ProgressEvent(
                timestamp=time.time(),
                step_name=step_name,
                step_index=step_index,
                total_steps=total_steps,
                event_type="started",
            )
        )

    def step_completed(
        self,
        step_name: str,
        step_index: int,
        total_steps: int,
        duration_s: float,
        peak_mem_mb: float | None = None,
    ) -> None:
        """Convenience method for step completed events."""
        self.notify(
            ProgressEvent(
                timestamp=time.time(),
                step_name=step_name,
                step_index=step_index,
                total_steps=total_steps,
                event_type="completed",
                duration_s=duration_s,
                peak_mem_mb=peak_mem_mb,
            )
        )

    def step_failed(
        self,
        step_name: str,
        step_index: int,
        total_steps: int,
        duration_s: float,
        error: str,
    ) -> None:
        """Convenience method for step failed events."""
        self.notify(
            ProgressEvent(
                timestamp=time.time(),
                step_name=step_name,
                step_index=step_index,
                total_steps=total_steps,
                event_type="failed",
                duration_s=duration_s,
                error=error,
            )
        )

    def step_progress(
        self,
        step_name: str,
        step_index: int,
        total_steps: int,
        current: int,
        total: int,
        message: str | None = None,
    ) -> None:
        """Convenience method for sub-step progress events."""
        self.notify(
            ProgressEvent(
                timestamp=time.time(),
                step_name=step_name,
                step_index=step_index,
                total_steps=total_steps,
                event_type="progress",
                current=current,
                total=total,
                message=message,
            )
        )
