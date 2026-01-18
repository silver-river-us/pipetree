"""Test fixtures for the ingestion framework tests."""

from dataclasses import dataclass, field
from typing import Any

from pipetree import Context


@dataclass
class MockContext(Context):
    """Flexible mock context with common fields for testing."""

    # Common fields used in tests
    path: str | None = None
    a: Any = None
    b: Any = None
    result: Any = None
    value: Any = None
    output: Any = None
    signal: Any = None
    kind: str | None = None
    scanned: bool | None = None
    order: list[Any] = field(default_factory=list)
    x: Any = None
