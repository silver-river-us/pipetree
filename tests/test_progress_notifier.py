"""Tests for progress notification system."""

import tempfile
from pathlib import Path

import pytest

from pipetree import (
    Capability,
    FileProgressNotifier,
    InMemoryProgressNotifier,
    NullProgressNotifier,
    Pipetree,
    ProgressEvent,
    Step,
)
from pipetree.types import Context
from tests.fixtures import MockContext


class TestProgressEvent:
    def test_event_creation(self) -> None:
        event = ProgressEvent(
            timestamp=1234567890.123,
            step_name="test_step",
            step_index=0,
            total_steps=3,
            event_type="started",
        )
        assert event.step_name == "test_step"
        assert event.event_type == "started"
        assert event.duration_s is None

    def test_event_with_all_fields(self) -> None:
        event = ProgressEvent(
            timestamp=1234567890.123,
            step_name="test_step",
            step_index=1,
            total_steps=3,
            event_type="progress",
            duration_s=1.5,
            error=None,
            current=50,
            total=100,
            message="Processing...",
        )
        assert event.current == 50
        assert event.total == 100
        assert event.message == "Processing..."


class TestNullProgressNotifier:
    def test_does_nothing(self) -> None:
        notifier = NullProgressNotifier()
        # Should not raise
        notifier.step_started("step", 0, 1)
        notifier.step_completed("step", 0, 1, 1.0)
        notifier.step_progress("step", 0, 1, 50, 100)
        notifier.close()


class TestInMemoryProgressNotifier:
    def test_stores_events(self) -> None:
        notifier = InMemoryProgressNotifier()
        notifier.step_started("step1", 0, 2)
        notifier.step_completed("step1", 0, 2, 0.5)

        assert len(notifier.events) == 2
        assert notifier.events[0].event_type == "started"
        assert notifier.events[1].event_type == "completed"
        assert notifier.events[1].duration_s == 0.5

    def test_stores_progress_events(self) -> None:
        notifier = InMemoryProgressNotifier()
        notifier.step_progress("extract", 0, 1, 5, 100, "Page 5")

        assert len(notifier.events) == 1
        event = notifier.events[0]
        assert event.event_type == "progress"
        assert event.current == 5
        assert event.total == 100
        assert event.message == "Page 5"

    def test_clear(self) -> None:
        notifier = InMemoryProgressNotifier()
        notifier.step_started("step1", 0, 1)
        notifier.clear()
        assert len(notifier.events) == 0


class TestFileProgressNotifier:
    def test_writes_csv_header(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "progress.csv"
            notifier = FileProgressNotifier(path)
            notifier.close()

            content = path.read_text()
            assert "timestamp" in content
            assert "step_name" in content
            assert "event_type" in content

    def test_writes_events_to_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "progress.csv"
            notifier = FileProgressNotifier(path)
            notifier.step_started("load_pdf", 0, 3)
            notifier.step_completed("load_pdf", 0, 3, 0.5)
            notifier.close()

            content = path.read_text()
            lines = content.strip().split("\n")
            assert len(lines) == 3  # header + 2 events
            assert "load_pdf" in lines[1]
            assert "started" in lines[1]
            assert "completed" in lines[2]

    def test_writes_progress_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "progress.csv"
            notifier = FileProgressNotifier(path)
            notifier.step_progress("extract", 1, 3, 50, 100, "Halfway")
            notifier.close()

            content = path.read_text()
            assert "progress" in content
            assert "50" in content
            assert "100" in content
            assert "Halfway" in content

    def test_creates_parent_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "subdir" / "progress.csv"
            notifier = FileProgressNotifier(path)
            notifier.close()
            assert path.exists()


class TestPipetreeWithProgress:
    @pytest.mark.asyncio
    async def test_emits_started_and_completed_events(self) -> None:
        cap = Capability(name="test", requires=set(), provides={"result"})

        class TestStep(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "done"  # type: ignore
                return ctx

        notifier = InMemoryProgressNotifier()
        pipeline = Pipetree(
            steps=[TestStep(cap, "step1")],
            progress_notifier=notifier,
        )

        await pipeline.run(MockContext())

        assert len(notifier.events) == 2
        assert notifier.events[0].event_type == "started"
        assert notifier.events[0].step_name == "step1"
        assert notifier.events[1].event_type == "completed"
        assert notifier.events[1].duration_s is not None

    @pytest.mark.asyncio
    async def test_emits_failed_event_on_error(self) -> None:
        cap = Capability(name="test", requires=set(), provides={"result"})

        class FailingStep(Step):
            def run(self, ctx: Context) -> Context:
                raise ValueError("Something went wrong")

        notifier = InMemoryProgressNotifier()
        pipeline = Pipetree(
            steps=[FailingStep(cap, "failing_step")],
            progress_notifier=notifier,
        )

        with pytest.raises(ValueError):
            await pipeline.run(MockContext())

        assert len(notifier.events) == 2
        assert notifier.events[0].event_type == "started"
        assert notifier.events[1].event_type == "failed"
        assert notifier.events[1].error == "Something went wrong"

    @pytest.mark.asyncio
    async def test_step_can_report_progress(self) -> None:
        cap = Capability(name="test", requires=set(), provides={"result"})

        class ProgressReportingStep(Step):
            def run(self, ctx: Context) -> Context:
                for i in range(5):
                    ctx.report_progress(i + 1, 5, f"Item {i + 1}")
                ctx.result = "done"  # type: ignore
                return ctx

        notifier = InMemoryProgressNotifier()
        pipeline = Pipetree(
            steps=[ProgressReportingStep(cap, "progress_step")],
            progress_notifier=notifier,
        )

        await pipeline.run(MockContext())

        # 1 started + 5 progress + 1 completed = 7 events
        assert len(notifier.events) == 7
        progress_events = [e for e in notifier.events if e.event_type == "progress"]
        assert len(progress_events) == 5
        assert progress_events[0].current == 1
        assert progress_events[4].current == 5

    @pytest.mark.asyncio
    async def test_multiple_steps_with_progress(self) -> None:
        cap1 = Capability(name="step1", requires=set(), provides={"a"})
        cap2 = Capability(name="step2", requires={"a"}, provides={"b"})

        class Step1(Step):
            def run(self, ctx: Context) -> Context:
                ctx.a = 1  # type: ignore
                return ctx

        class Step2(Step):
            def run(self, ctx: Context) -> Context:
                ctx.b = 2  # type: ignore
                return ctx

        notifier = InMemoryProgressNotifier()
        pipeline = Pipetree(
            steps=[Step1(cap1, "step1"), Step2(cap2, "step2")],
            progress_notifier=notifier,
        )

        await pipeline.run(MockContext())

        # 2 steps x (started + completed) = 4 events
        assert len(notifier.events) == 4
        assert notifier.events[0].step_name == "step1"
        assert notifier.events[0].step_index == 0
        assert notifier.events[0].total_steps == 2
        assert notifier.events[2].step_name == "step2"
        assert notifier.events[2].step_index == 1

    @pytest.mark.asyncio
    async def test_no_notifier_works(self) -> None:
        cap = Capability(name="test", requires=set(), provides={"result"})

        class TestStep(Step):
            def run(self, ctx: Context) -> Context:
                ctx.result = "done"  # type: ignore
                return ctx

        # No notifier - should not raise
        pipeline = Pipetree(steps=[TestStep(cap, "step1")])
        result = await pipeline.run(MockContext())
        assert result.result == "done"
