"""Progress notification infrastructure."""

from pipetree import HTTPProgressNotifier


def create_notifier(
    pipeline_name: str,
    base_url: str,
    api_key: str,
) -> HTTPProgressNotifier | None:
    """Create an HTTP progress notifier, or None if no API key is set."""
    if not api_key:
        return None

    return HTTPProgressNotifier(
        base_url=base_url,
        api_key=api_key,
        pipeline=pipeline_name,
    )
