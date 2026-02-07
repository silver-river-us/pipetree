"""PDF text extraction implementations for benchmarking.

Each extractor implements the TEXT_EXTRACTION capability using a different
PDF library. All use the same chunked parallel processing strategy.
"""

import os
import sys
import time
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, as_completed

from pipetree import Capability, Registry, Step

from lib.context import PdfContext

from .workers import (
    extract_pdfplumber_chunk,
    extract_pymupdf_chunk,
    extract_pypdf_chunk,
)

# Capability contract
TEXT_EXTRACTION = Capability(
    name="text_extraction",
    requires={"pdf", "path", "total_pages"},
    provides={"texts"},
)

# Registry for implementations
registry = Registry()


def _print_progress(current: int, total: int, name: str, width: int = 30) -> None:
    """Print a progress bar that updates in place."""
    pct = current / total if total > 0 else 0
    filled = int(width * pct)
    bar = "█" * filled + "░" * (width - filled)
    sys.stdout.write(f"\r[{name}] {bar} {current}/{total} pages ({pct:.0%})")
    sys.stdout.flush()
    if current == total:
        sys.stdout.write("\n")


def _make_chunks(total: int, num_chunks: int) -> list[tuple[int, int]]:
    """Divide pages into roughly equal chunks."""
    if num_chunks <= 0:
        return [(0, total)]
    chunk_size = max(1, total // num_chunks)
    chunks = []
    start = 0
    for i in range(num_chunks):
        end = start + chunk_size
        if i == num_chunks - 1:
            end = total
        if start < total:
            chunks.append((start, end))
        start = end
    return chunks


class ChunkedExtractor(Step):
    """Base class for chunked parallel text extraction."""

    name: str = "base"
    worker_fn: Callable[[str, int, int], list[tuple[int, str]]]

    def run(self, ctx: PdfContext) -> PdfContext:  # type: ignore[override]
        if not ctx.pdf:
            raise ValueError("PDF not loaded")

        num_pages = ctx.total_pages
        num_workers = min(os.cpu_count() or 1, num_pages)
        chunks = _make_chunks(num_pages, num_workers)

        start_time = time.perf_counter()
        all_results: list[tuple[int, str]] = []
        completed = 0

        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            futures = {
                executor.submit(self.worker_fn, ctx.path, s, e): (s, e)
                for s, e in chunks
            }
            for future in as_completed(futures):
                results = future.result()
                all_results.extend(results)
                completed += len(results)
                ctx.report_progress(
                    completed, num_pages, f"{self.name}: {completed}/{num_pages}"
                )
                _print_progress(completed, num_pages, self.name)

        all_results.sort(key=lambda x: x[0])
        ctx.texts = [text for _, text in all_results]

        elapsed = time.perf_counter() - start_time
        print(
            f"  -> {elapsed:.2f}s ({num_pages / elapsed:.1f} pages/sec, {len(chunks)} chunks)"
        )
        return ctx


class PyPdfExtractor(ChunkedExtractor):
    """pypdf - pure Python, good balance of speed and features."""

    name = "pypdf"
    worker_fn = staticmethod(extract_pypdf_chunk)


class PdfPlumberExtractor(ChunkedExtractor):
    """pdfplumber - built on pdfminer, excellent for tables."""

    name = "pdfplumber"
    worker_fn = staticmethod(extract_pdfplumber_chunk)


class PyMuPdfExtractor(ChunkedExtractor):
    """PyMuPDF (fitz) - C-based, fastest option."""

    name = "pymupdf"
    worker_fn = staticmethod(extract_pymupdf_chunk)


# Register implementations
@registry.decorator("text_extraction", "pypdf")
def _create_pypdf() -> Step:
    return PyPdfExtractor(TEXT_EXTRACTION, "pypdf")


@registry.decorator("text_extraction", "pdfplumber")
def _create_pdfplumber() -> Step:
    return PdfPlumberExtractor(TEXT_EXTRACTION, "pdfplumber")


@registry.decorator("text_extraction", "pymupdf")
def _create_pymupdf() -> Step:
    return PyMuPdfExtractor(TEXT_EXTRACTION, "pymupdf")
