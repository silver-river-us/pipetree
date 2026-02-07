"""Tests for Context class methods."""

from dataclasses import dataclass, field

import pytest

from pipetree import Context


@dataclass
class ContextTestContext(Context):
    """Test context for context coverage tests."""

    name: str | None = None
    value: int | None = None
    items: list[str] = field(default_factory=list)
    _private_field: str = "private"  # Should be excluded from keys()


class TestContextKeys:
    """Test Context.keys() method."""

    def test_keys_excludes_private_fields(self) -> None:
        """Test that keys() excludes fields starting with underscore."""
        ctx = ContextTestContext(name="test", value=5)

        keys = ctx.keys()

        # _private_field should NOT be in keys even though it has a value
        assert "_private_field" not in keys
        # Public fields should be present
        assert "name" in keys
        assert "value" in keys


class TestContextGet:
    """Test Context.get() method."""

    def test_get_returns_default_when_value_is_none(self) -> None:
        """Test that get() returns default when attribute is None."""
        ctx = ContextTestContext(name=None)

        # value is None, should return default
        result = ctx.get("name", "default_name")
        assert result == "default_name"

    def test_get_returns_value_when_set(self) -> None:
        """Test that get() returns actual value when set."""
        ctx = ContextTestContext(name="actual_name")

        result = ctx.get("name", "default_name")
        assert result == "actual_name"

    def test_get_returns_default_for_nonexistent_attr(self) -> None:
        """Test that get() returns default for non-existent attribute."""
        ctx = ContextTestContext()

        result = ctx.get("nonexistent", "default")
        assert result == "default"


class TestContextSet:
    """Test Context.set() method."""

    def test_set_raises_for_undefined_attribute(self) -> None:
        """Test that set() raises AttributeError for undefined attributes."""
        ctx = ContextTestContext()

        with pytest.raises(AttributeError) as exc_info:
            ctx.set("undefined_attr", "value")

        assert "has no attribute" in str(exc_info.value)
        assert "undefined_attr" in str(exc_info.value)
        assert "Define it in your context class" in str(exc_info.value)

    def test_set_works_for_defined_attribute(self) -> None:
        """Test that set() works for defined attributes."""
        ctx = ContextTestContext()

        ctx.set("name", "new_name")
        assert ctx.name == "new_name"


class TestContextReportProgress:
    """Test Context.report_progress() method."""

    def test_report_progress_calls_notifier(self) -> None:
        """Test that report_progress calls notifier.step_progress."""

        class MockNotifier:
            def __init__(self):
                self.calls = []

            def step_progress(
                self,
                step_name: str,
                step_index: int,
                total_steps: int,
                current: int,
                total: int,
                message: str | None,
            ):
                self.calls.append(
                    {
                        "step_name": step_name,
                        "step_index": step_index,
                        "total_steps": total_steps,
                        "current": current,
                        "total": total,
                        "message": message,
                    }
                )

        ctx = ContextTestContext()
        notifier = MockNotifier()

        ctx._notifier = notifier
        ctx._step_name = "test_step"
        ctx._step_index = 2
        ctx._total_steps = 5

        ctx.report_progress(10, 100, "Processing...")

        assert len(notifier.calls) == 1
        assert notifier.calls[0] == {
            "step_name": "test_step",
            "step_index": 2,
            "total_steps": 5,
            "current": 10,
            "total": 100,
            "message": "Processing...",
        }

    def test_report_progress_does_nothing_without_step_name(self) -> None:
        """Test that report_progress does nothing when step_name is None."""

        class MockNotifier:
            def __init__(self):
                self.calls = []

            def step_progress(self, *args, **kwargs):
                self.calls.append(args)

        ctx = ContextTestContext()
        notifier = MockNotifier()

        ctx._notifier = notifier
        ctx._step_name = None  # No step name

        ctx.report_progress(10, 100, "Processing...")

        # Should not have called notifier
        assert len(notifier.calls) == 0
