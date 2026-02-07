"""Progress notification implementations."""

from pipetree.infrastructure.progress.benchmark_store import BenchmarkStore
from pipetree.infrastructure.progress.file_progress_notifier import (
    FileProgressNotifier,
)

try:
    from pipetree.infrastructure.progress.http_benchmark_store import (
        HTTPBenchmarkStore,
    )
except ImportError:  # pragma: no cover
    HTTPBenchmarkStore = None  # type: ignore[assignment,misc]
try:
    from pipetree.infrastructure.progress.http_progress_notifier import (
        HTTPProgressNotifier,
    )
except ImportError:  # pragma: no cover
    HTTPProgressNotifier = None  # type: ignore[assignment,misc]
from pipetree.infrastructure.progress.handler import (
    ConsoleProgressHandler,
    ProgressHandler,
)
from pipetree.infrastructure.progress.in_memory_progress_notifier import (
    InMemoryProgressNotifier,
)
from pipetree.infrastructure.progress.null_progress_notifier import (
    NullProgressNotifier,
)
from pipetree.infrastructure.progress.progress_notifier import (
    ProgressEvent,
    ProgressNotifier,
)
from pipetree.infrastructure.progress.sqlite_progress_notifier import (
    SQLiteProgressNotifier,
)
from pipetree.infrastructure.progress.sqlite_watcher import (
    SQLiteProgressWatcher,
    watch_progress,
)

__all__ = [
    "BenchmarkStore",
    "ConsoleProgressHandler",
    "HTTPBenchmarkStore",
    "ProgressEvent",
    "ProgressHandler",
    "ProgressNotifier",
    "NullProgressNotifier",
    "InMemoryProgressNotifier",
    "FileProgressNotifier",
    "HTTPProgressNotifier",
    "SQLiteProgressNotifier",
    "SQLiteProgressWatcher",
    "watch_progress",
]
