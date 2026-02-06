"""Tests for visualizer.lib.formatters."""

from lib.formatters import (
    format_duration,
    format_timestamp,
    get_status_color,
    organize_steps_with_branches,
)


class TestFormatDuration:
    def test_none(self) -> None:
        assert format_duration(None) == "-"

    def test_milliseconds(self) -> None:
        assert format_duration(0.5) == "500ms"
        assert format_duration(0.001) == "1ms"

    def test_seconds(self) -> None:
        assert format_duration(1.5) == "1.50s"
        assert format_duration(30) == "30.00s"

    def test_minutes(self) -> None:
        assert format_duration(90) == "1m 30s"
        assert format_duration(125.5) == "2m 6s"

    def test_hours_with_seconds(self) -> None:
        assert format_duration(3661) == "1h 1m 1s"
        assert format_duration(7261.5) == "2h 1m 2s"

    def test_hours_without_seconds(self) -> None:
        assert format_duration(3600) == "1h 0m"
        assert format_duration(7200) == "2h 0m"


class TestFormatTimestamp:
    def test_none(self) -> None:
        assert format_timestamp(None) == "-"

    def test_returns_span_with_data_ts(self) -> None:
        result = format_timestamp(1700000000.0)
        assert 'class="local-time"' in result
        assert 'data-ts="1700000000.0"' in result


class TestGetStatusColor:
    def test_known_statuses(self) -> None:
        for status in ["pending", "running", "completed", "failed", "skipped"]:
            colors = get_status_color(status)
            assert "bg" in colors
            assert "text" in colors
            assert "border" in colors
            assert "icon" in colors

    def test_unknown_falls_back_to_pending(self) -> None:
        assert get_status_color("unknown") == get_status_color("pending")


class TestOrganizeStepsWithBranches:
    def test_empty(self) -> None:
        result = organize_steps_with_branches([])
        assert result["main"] == []
        assert result["branches"] == {}
        assert result["branch_tree"] == {}
        assert result["branches_by_parent"] == {}

    def test_main_steps_only(self) -> None:
        steps = [
            {"name": "step1", "step_index": 0},
            {"name": "step2", "step_index": 1},
        ]
        result = organize_steps_with_branches(steps)
        assert len(result["main"]) == 2
        assert result["branches"] == {}
        assert result["branch_tree"] == {}

    def test_with_branches(self) -> None:
        steps = [
            {"name": "load", "step_index": 0},
            {"name": "route_main", "step_index": 1},
            {
                "name": "process_a",
                "step_index": 2,
                "branch": "a",
                "parent_step": "route_main",
            },
            {
                "name": "process_b",
                "step_index": 3,
                "branch": "b",
                "parent_step": "route_main",
            },
        ]
        result = organize_steps_with_branches(steps)
        assert len(result["main"]) == 2
        assert "a" in result["branches"]
        assert "b" in result["branches"]
        assert "a" in result["branch_tree"]
        assert "b" in result["branch_tree"]

    def test_nested_branches(self) -> None:
        """Covers recursive build_branch_tree (line 100)."""
        steps = [
            {"name": "load", "step_index": 0},
            {"name": "route_top", "step_index": 1},
            {
                "name": "sub_router",
                "step_index": 2,
                "branch": "branch_a",
                "parent_step": "route_top",
            },
            {
                "name": "leaf_step",
                "step_index": 3,
                "branch": "branch_a1",
                "parent_step": "sub_router",
            },
        ]
        result = organize_steps_with_branches(steps)
        assert len(result["main"]) == 2
        tree = result["branch_tree"]
        assert "branch_a" in tree
        # Nested children from recursive call
        assert "branch_a1" in tree["branch_a"]["children"]

    def test_no_router_step(self) -> None:
        """When no step starts with route_, branch_tree is empty."""
        steps = [
            {"name": "load", "step_index": 0},
            {"name": "process", "step_index": 1},
            {
                "name": "sub",
                "step_index": 2,
                "branch": "x",
                "parent_step": "process",
            },
        ]
        result = organize_steps_with_branches(steps)
        assert result["branch_tree"] == {}
        assert "x" in result["branches"]
        assert "x" in result["flat_branches"] if "flat_branches" in result else True
