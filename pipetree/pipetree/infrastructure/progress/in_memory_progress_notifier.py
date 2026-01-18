"""In-memory progress notifier for testing."""

from pipetree.infrastructure.progress.progress_notifier import (
    ProgressEvent,
    ProgressNotifier,
)


class InMemoryProgressNotifier(ProgressNotifier):
    """Stores progress events in memory. Useful for testing."""

    def __init__(self) -> None:
        self.events: list[ProgressEvent] = []

    def notify(self, event: ProgressEvent) -> None:
        """Store event in memory."""
        self.events.append(event)

    def clear(self) -> None:
        """Clear all stored events."""
        self.events.clear()
