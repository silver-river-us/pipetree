"""Extract text step using PyMuPDF with chunked parallel processing.

PyMuPDF (fitz) was selected based on benchmarks:
- pymupdf:    1.37s  (winner)
- pypdf:      20.39s (15x slower)
- pdfplumber: 100.49s (73x slower)

Memory optimization: Streams extracted text to disk instead of accumulating
in memory, reducing peak memory usage from O(total_text) to O(chunk_size).
"""

import os
import time
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed

from pipetree import Step

from ..context import PdfContext


def _extract_chunk(pdf_path: str, start: int, end: int) -> list[tuple[int, str]]:
    """Extract text from a chunk of pages. Runs in a separate process."""
    warnings.filterwarnings("ignore", message=".*global interpreter lock.*")
    import fitz

    doc = fitz.open(pdf_path)
    results = [(i, doc[i].get_text() or "") for i in range(start, end)]
    doc.close()
    return results


def _make_chunks(total: int, num_chunks: int) -> list[tuple[int, int]]:
    """Divide pages into roughly equal chunks."""
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


class ExtractTextStep(Step):
    """Extract text from PDF pages using PyMuPDF with chunked parallel processing.

    Streams results to disk to minimize memory footprint.
    """

    def run(self, ctx: PdfContext) -> PdfContext:  # type: ignore[override]
        if not ctx.pdf:
            raise ValueError("PDF not loaded")

        num_pages = ctx.total_pages
        num_workers = min(os.cpu_count() or 1, num_pages)
        chunks = _make_chunks(num_pages, num_workers)

        print(
            f"Extracting text from {num_pages} pages "
            f"({len(chunks)} chunks, {num_workers} workers)..."
        )
        start_time = time.perf_counter()

        # Collect results with page indices for ordering
        pending_results: dict[int, str] = {}
        next_page_to_write = 0
        completed = 0

        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            futures = {
                executor.submit(_extract_chunk, ctx.path, start, end): (start, end)
                for start, end in chunks
            }

            for future in as_completed(futures):
                chunk_results = future.result()

                # Store results temporarily
                for page_idx, text in chunk_results:
                    pending_results[page_idx] = text

                # Stream to file in order (write pages as soon as they're ready)
                while next_page_to_write in pending_results:
                    ctx.texts.append(pending_results.pop(next_page_to_write))
                    next_page_to_write += 1

                completed += len(chunk_results)
                ctx.report_progress(
                    completed, num_pages, f"Extracted {completed}/{num_pages} pages"
                )

        # Write any remaining pages (shouldn't happen if logic is correct)
        for page_idx in sorted(pending_results.keys()):
            ctx.texts.append(pending_results[page_idx])

        ctx.texts.finalize()

        elapsed = time.perf_counter() - start_time
        pages_per_sec = num_pages / elapsed if elapsed > 0 else 0
        print(
            f"Extracted {num_pages} pages in {elapsed:.2f}s ({pages_per_sec:.1f} pages/sec)"
        )

        return ctx
