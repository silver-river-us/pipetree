"""Benchmark test for sorting implementations."""

import pytest
from pipetree import BenchRunner, Fixture

from registry import registry


def test_sorting(
    benchmark_store,
    sorting_fixtures: list[Fixture],
) -> None:
    """Compare bubble sort, insertion sort, and Python's builtin sorted()."""
    if not sorting_fixtures:
        pytest.skip("No fixtures")

    runner = BenchRunner(
        registry=registry,
        track_memory=True,
        store=benchmark_store,
    )

    results = runner.run_step_ab(
        cap_name="sorting",
        impls=["bubble", "insertion", "builtin"],
        fixtures=sorting_fixtures,
        judge=lambda fixture, ctx: {
            "correctness": float(ctx["sorted"] == sorted(fixture["items"])),
            "items_processed": len(fixture["items"]),
        },
        setup_ctx=lambda fixture: {"items": fixture["items"]},
        name="Sorting Algorithm Comparison",
        description="Compare bubble sort, insertion sort, and Python builtin",
    )

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    for r in results:
        if r.error:
            print(f"\n{r.impl_name} ({r.fixture_id}): ERROR - {r.error}")
        else:
            m = r.metrics
            print(
                f"\n{r.impl_name} ({r.fixture_id}):"
                f"\n  Time: {m.get('wall_time_s', 0):.4f}s"
                f"\n  Memory: {m.get('peak_mem_mb', 0):.2f} MB"
                f"\n  Correctness: {m.get('correctness', 0):.0%}"
            )
    print("=" * 60)

    for r in results:
        assert r.error is None, f"{r.impl_name} failed: {r.error}"
        assert r.metrics.get("correctness") == 1.0
