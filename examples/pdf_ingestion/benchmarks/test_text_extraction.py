"""Benchmark test for PDF text extraction libraries."""

import pytest
from pipetree import BenchmarkStore, BenchRunner, Fixture

from .conftest import judge_extraction, setup_context
from .extractors import registry


def test_text_extraction(
    benchmark_store: BenchmarkStore,
    pdf_fixtures: list[Fixture],
) -> None:
    """Compare pypdf, pdfplumber, and pymupdf text extraction."""
    if not pdf_fixtures:
        pytest.skip("No PDF fixtures found")

    runner = BenchRunner(
        registry=registry,
        track_memory=True,
        store=benchmark_store,
    )

    results = runner.run_step_ab(
        cap_name="text_extraction",
        impls=["pypdf", "pdfplumber", "pymupdf"],
        fixtures=pdf_fixtures,
        judge=judge_extraction,
        setup_ctx=setup_context,
        name="PDF Library Comparison",
        description="Compare text extraction across pypdf, pdfplumber, and PyMuPDF",
    )

    # Print summary
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    for r in results:
        if r.error:
            print(f"\n{r.impl_name}: ERROR - {r.error}")
        else:
            m = r.metrics
            print(f"\n{r.impl_name}:")
            print(f"  Time: {m.get('wall_time_s', 0):.2f}s")
            print(f"  Memory: {m.get('peak_mem_mb', 0):.1f} MB")
            print(f"  Correctness: {m.get('correctness', 0):.1%}")
    print("=" * 60)

    # Assertions
    assert len(results) == 3
    for r in results:
        assert r.error is None, f"{r.impl_name} failed: {r.error}"
