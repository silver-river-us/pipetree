"""Pipeline context - the streaming data bus."""

from dataclasses import dataclass, fields
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


@dataclass
class Context:
    """
    Base context class for pipeline data.

    Users should inherit from this class and define their own typed attributes.
    The capability system uses `keys()` to check which attributes are set.

    Example:
        @dataclass
        class PdfContext(Context):
            path: str
            pdf: Any = None
            pages: list[Any] | None = None
            texts: list[str] | None = None
            chunks: list[Chunk] | None = None
    """

    def __post_init__(self) -> None:
        # Internal progress tracking (set dynamically to avoid dataclass inheritance issues)
        self._notifier: Any = None
        self._step_name: str | None = None
        self._step_index: int = 0
        self._total_steps: int = 0

    def keys(self) -> set[str]:
        """
        Get the set of attribute names that are considered 'set'.

        An attribute is 'set' if it has a non-None value.
        Internal fields (starting with _) are excluded.
        """
        result: set[str] = set()
        for f in fields(self):
            if f.name.startswith("_"):
                continue
            value = getattr(self, f.name)
            if value is not None:
                result.add(f.name)
        return result

    def report_progress(
        self, current: int, total: int, message: str | None = None
    ) -> None:
        """
        Report sub-step progress (e.g., page 5 of 100).

        Can be called by steps to report their internal progress.
        Does nothing if no notifier is configured.
        """
        notifier = getattr(self, "_notifier", None)
        step_name = getattr(self, "_step_name", None)
        if notifier is not None and step_name is not None:
            notifier.step_progress(
                step_name,
                getattr(self, "_step_index", 0),
                getattr(self, "_total_steps", 0),
                current,
                total,
                message,
            )

    def has(self, key: str) -> bool:
        """Check if an attribute is set."""
        return key in self.keys()

    def get(self, key: str, default: Any = None) -> Any:
        """Get an attribute value with a default."""
        if hasattr(self, key):
            value = getattr(self, key)
            return value if value is not None else default
        return default

    def set(self, key: str, value: Any) -> None:
        """Set an attribute value."""
        if not hasattr(self, key):
            raise AttributeError(
                f"{self.__class__.__name__} has no attribute {key!r}. "
                f"Define it in your context class."
            )
        setattr(self, key, value)
