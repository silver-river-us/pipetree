"""Test fixture for benchmarking."""

from typing import Any, TypedDict


class Fixture(TypedDict, total=False):
    """Test fixture for benchmarking."""

    id: str
    path: str
    page_range: tuple[int, int]
    expected: dict[str, Any]  # gold snippets/fields/labels/questions
