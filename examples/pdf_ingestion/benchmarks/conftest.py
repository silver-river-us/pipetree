"""Pytest fixtures for benchmarks."""

from pathlib import Path

import pytest
from pipetree import BenchmarkStore, Fixture, Metrics
from pypdf import PdfReader

from pdf_ingestion.context import PdfContext

ASSETS_DIR = Path(__file__).parent.parent / "assets"
DB_PATH = Path(__file__).parent.parent / "db" / "benchmarks.db"


@pytest.fixture
def benchmark_store() -> BenchmarkStore:
    """SQLite store for persisting benchmark results."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return BenchmarkStore(DB_PATH)


@pytest.fixture
def pdf_fixtures() -> list[Fixture]:
    """PDF files to benchmark against."""
    fixtures: list[Fixture] = []

    medium_pdf = ASSETS_DIR / "medium.pdf"
    if medium_pdf.exists():
        reader = PdfReader(medium_pdf)
        fixtures.append({
            "id": "medium.pdf",
            "path": str(medium_pdf),
            "expected": {"page_count": len(reader.pages)},
        })

    return fixtures


def setup_context(fixture: Fixture) -> PdfContext:
    """Create a PdfContext from a fixture."""
    pdf_path = fixture.get("path", "")
    reader = PdfReader(pdf_path)
    return PdfContext(
        path=pdf_path,
        output_path=None,
        pdf=True,
        total_pages=len(reader.pages),
    )


def judge_extraction(fixture: Fixture, ctx: PdfContext) -> Metrics:
    """Score extraction quality based on non-empty pages."""
    texts = ctx.texts
    non_empty = sum(1 for t in texts if t.strip())
    total = len(texts)

    return {
        "correctness": non_empty / total if total > 0 else 0.0,
        "items_processed": total,
    }
