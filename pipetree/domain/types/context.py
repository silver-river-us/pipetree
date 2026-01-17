"""Pipeline context - the streaming data bus."""

from dataclasses import dataclass, fields
from typing import Any


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

    def keys(self) -> set[str]:
        """
        Get the set of attribute names that are considered 'set'.

        An attribute is 'set' if it has a non-None value.
        """
        result: set[str] = set()
        for f in fields(self):
            value = getattr(self, f.name)
            if value is not None:
                result.add(f.name)
        return result

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
