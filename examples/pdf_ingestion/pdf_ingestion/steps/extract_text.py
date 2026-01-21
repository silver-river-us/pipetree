"""Extract text step using pdfplumber with parallel processing.

pdfplumber is built on pdfminer and provides excellent text extraction,
especially for documents with tables and complex layouts.

Performance: Uses ProcessPoolExecutor for true parallelism.
"""

import contextlib
import os
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pdfplumber
from pipetree import Step, step

from ..context import PdfContext

# Optimal worker count
_MAX_WORKERS = 8


def _extract_pages_to_file(
    pdf_path: str,
    start: int,
    end: int,
    output_path: str,
) -> int:
    """Extract text from a range of pages and write to temp file."""
    with (
        pdfplumber.open(pdf_path) as pdf,
        open(output_path, "w", encoding="utf-8") as f,
    ):
        for i in range(start, end):
            text = pdf.pages[i].extract_text() or ""
            f.write(f"{i}\t{len(text)}\n")
            f.write(text)
    return end - start


@step(requires={"pdf"}, provides={"texts"})
class ExtractText(Step):
    """Extract text from PDF pages using pdfplumber with parallel processing."""

    def run(self, ctx: PdfContext) -> PdfContext:  # type: ignore[override]
        if not ctx.pdf:
            raise ValueError("PDF not loaded")

        num_pages = ctx.total_pages
        num_workers = min(_MAX_WORKERS, num_pages, os.cpu_count() or 1)

        chunk_size = max(1, num_pages // num_workers)
        chunks = []
        for i in range(0, num_pages, chunk_size):
            chunks.append((i, min(i + chunk_size, num_pages)))

        print(
            f"Extracting text from {num_pages} pages "
            f"({len(chunks)} chunks, {num_workers} workers)..."
        )
        start_time = time.perf_counter()

        temp_dir = tempfile.mkdtemp(prefix="pdf_extract_")
        temp_files: dict[tuple[int, int], str] = {}

        try:
            with ProcessPoolExecutor(max_workers=num_workers) as executor:
                futures = {}
                for start, end in chunks:
                    temp_path = f"{temp_dir}/chunk_{start}_{end}.txt"
                    temp_files[(start, end)] = temp_path
                    futures[
                        executor.submit(
                            _extract_pages_to_file, ctx.path, start, end, temp_path
                        )
                    ] = (start, end)

                completed = 0
                for future in as_completed(futures):
                    count = future.result()
                    completed += count
                    ctx.report_progress(
                        completed, num_pages, f"Extracted {completed}/{num_pages} pages"
                    )

            # Merge temp files in page order
            results: dict[int, str] = {}
            for (_start, _end), temp_path in sorted(temp_files.items()):
                with open(temp_path, encoding="utf-8") as f:
                    content = f.read()
                    pos = 0
                    while pos < len(content):
                        newline_pos = content.index("\n", pos)
                        header = content[pos:newline_pos]
                        page_idx_str, text_len_str = header.split("\t")
                        page_idx = int(page_idx_str)
                        text_len = int(text_len_str)
                        text_start = newline_pos + 1
                        text_end = text_start + text_len
                        results[page_idx] = content[text_start:text_end]
                        pos = text_end

            for i in range(num_pages):
                ctx.texts.append(results[i])
                del results[i]

            ctx.texts.finalize()

        finally:
            for temp_path in temp_files.values():
                with contextlib.suppress(OSError):
                    Path(temp_path).unlink()
            with contextlib.suppress(OSError):
                Path(temp_dir).rmdir()

        elapsed = time.perf_counter() - start_time
        pages_per_sec = num_pages / elapsed if elapsed > 0 else 0
        print(
            f"Extracted {num_pages} pages in {elapsed:.2f}s ({pages_per_sec:.1f} pages/sec)"
        )

        return ctx
