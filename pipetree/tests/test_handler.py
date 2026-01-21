"""Tests for progress handlers."""

import io
import sys
from unittest.mock import patch

from pipetree.infrastructure.progress.handler import (
    ConsoleProgressHandler,
    ProgressHandler,
)


class TestProgressHandlerProtocol:
    """Test ProgressHandler protocol compliance."""

    def test_protocol_methods_exist(self) -> None:
        """Verify protocol defines all required methods."""
        # Check protocol has the expected methods
        assert hasattr(ProgressHandler, "on_started")
        assert hasattr(ProgressHandler, "on_completed")
        assert hasattr(ProgressHandler, "on_failed")
        assert hasattr(ProgressHandler, "on_progress")
        assert hasattr(ProgressHandler, "on_cleanup")


class TestConsoleProgressHandler:
    """Test ConsoleProgressHandler implementation."""

    def test_on_started_prints_message(self) -> None:
        """Test that on_started prints the correct message."""
        handler = ConsoleProgressHandler()
        with patch("builtins.print") as mock_print:
            handler.on_started("test_step")
            mock_print.assert_called_with("[test_step] Started")

    def test_on_completed_prints_with_duration(self) -> None:
        """Test that on_completed prints duration when provided."""
        handler = ConsoleProgressHandler()
        with patch("builtins.print") as mock_print:
            handler.on_completed("test_step", 1.5)
            mock_print.assert_called_with("[test_step] Completed in 1.50s")

    def test_on_completed_prints_without_duration(self) -> None:
        """Test that on_completed prints without duration when None."""
        handler = ConsoleProgressHandler()
        with patch("builtins.print") as mock_print:
            handler.on_completed("test_step", None)
            mock_print.assert_called_with("[test_step] Completed")

    def test_on_failed_prints_error(self) -> None:
        """Test that on_failed prints the error message."""
        handler = ConsoleProgressHandler()
        with patch("builtins.print") as mock_print:
            handler.on_failed("test_step", "Something broke")
            mock_print.assert_called_with("[test_step] FAILED: Something broke")

    def test_on_progress_prints_progress_bar(self) -> None:
        """Test that on_progress prints a progress bar."""
        handler = ConsoleProgressHandler()

        # Capture stdout
        captured = io.StringIO()
        with patch.object(sys, "stdout", captured):
            handler.on_progress("test_step", 5, 10, "Processing")

        output = captured.getvalue()
        assert "[test_step]" in output
        assert "50.0%" in output
        assert "5/10" in output
        assert "Processing" in output

    def test_on_progress_with_no_message(self) -> None:
        """Test progress bar without a message."""
        handler = ConsoleProgressHandler()

        captured = io.StringIO()
        with patch.object(sys, "stdout", captured):
            handler.on_progress("test_step", 3, 10, None)

        output = captured.getvalue()
        assert "[test_step]" in output
        assert "30.0%" in output
        assert "3/10" in output

    def test_on_progress_zero_total_does_nothing(self) -> None:
        """Test that progress with zero total does nothing."""
        handler = ConsoleProgressHandler()

        captured = io.StringIO()
        with patch.object(sys, "stdout", captured):
            handler.on_progress("test_step", 0, 0, None)

        output = captured.getvalue()
        assert output == ""

    def test_on_cleanup_clears_progress_line(self) -> None:
        """Test that on_cleanup clears the progress line."""
        handler = ConsoleProgressHandler()

        # First print a progress line
        captured = io.StringIO()
        with patch.object(sys, "stdout", captured):
            handler.on_progress("test_step", 5, 10, "test")
            # Now cleanup
            handler.on_cleanup()

        # Should have written a carriage return and spaces to clear
        output = captured.getvalue()
        # The last operation should have cleared the line
        assert "\r" in output

    def test_clear_progress_line_clears_when_set(self) -> None:
        """Test that _clear_progress_line works when there's a progress line."""
        handler = ConsoleProgressHandler()

        # Set a progress line first
        captured = io.StringIO()
        with patch.object(sys, "stdout", captured):
            handler.on_progress("test_step", 5, 10, None)
            handler._clear_progress_line()

        # Should have cleared
        assert handler._last_progress_line == ""

    def test_clear_progress_line_noop_when_empty(self) -> None:
        """Test that _clear_progress_line is a no-op when no progress line."""
        handler = ConsoleProgressHandler()

        captured = io.StringIO()
        with patch.object(sys, "stdout", captured):
            handler._clear_progress_line()

        # Should have written nothing
        assert captured.getvalue() == ""

    def test_on_started_clears_previous_progress(self) -> None:
        """Test that on_started clears any previous progress line."""
        handler = ConsoleProgressHandler()

        captured = io.StringIO()
        with patch.object(sys, "stdout", captured):
            handler.on_progress("step1", 5, 10, None)
            with patch("builtins.print"):
                handler.on_started("step2")

        # Progress line should be cleared
        assert handler._last_progress_line == ""

    def test_on_completed_clears_previous_progress(self) -> None:
        """Test that on_completed clears any previous progress line."""
        handler = ConsoleProgressHandler()

        captured = io.StringIO()
        with patch.object(sys, "stdout", captured):
            handler.on_progress("step1", 5, 10, None)
            with patch("builtins.print"):
                handler.on_completed("step1", 1.0)

        # Progress line should be cleared
        assert handler._last_progress_line == ""

    def test_on_failed_clears_previous_progress(self) -> None:
        """Test that on_failed clears any previous progress line."""
        handler = ConsoleProgressHandler()

        captured = io.StringIO()
        with patch.object(sys, "stdout", captured):
            handler.on_progress("step1", 5, 10, None)
            with patch("builtins.print"):
                handler.on_failed("step1", "error")

        # Progress line should be cleared
        assert handler._last_progress_line == ""
