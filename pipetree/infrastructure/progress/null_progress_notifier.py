"""Null progress notifier - no-op implementation."""

from pipetree.infrastructure.progress.progress_notifier import (
    ProgressEvent,
    ProgressNotifier,
)


class NullProgressNotifier(ProgressNotifier):
    """No-op progress notifier. Used as default when no notifier is configured."""

    def notify(self, event: ProgressEvent) -> None:
        """Do nothing."""
        pass
