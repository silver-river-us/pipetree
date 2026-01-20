"""Extract text step using PyMuPDF with chunked parallel processing.

PyMuPDF (fitz) was selected based on benchmarks:
- pymupdf:    1.37s  (winner)
- pypdf:      20.39s (15x slower)
- pdfplumber: 100.49s (73x slower)

Performance optimization: Workers write directly to temp files instead of
returning text through IPC, eliminating pickle serialization overhead.

Memory optimization: Streams extracted text to disk instead of accumulating
in memory, reducing peak memory usage from O(total_text) to O(chunk_size).
"""

import json
import os
import shutil
import tempfile
import time
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from pipetree import Step, step

from ..context import PdfContext


def _extract_chunk_to_file(
    pdf_path: str, start: int, end: int, output_path: str
) -> tuple[int, int]:
    """Extract text from a chunk of pages directly to a file.

    Returns (start, page_count) instead of the actual text data,
    eliminating IPC serialization overhead for large text content.
    """
    warnings.filterwarnings("ignore", message=".*global interpreter lock.*")
    import fitz

    # TEXT_DEHYPHENATE joins hyphenated words at line breaks
    # TEXT_PRESERVE_WHITESPACE is faster but we need dehyphenation for quality
    flags = fitz.TEXT_DEHYPHENATE

    doc = fitz.open(pdf_path)
    with open(output_path, "w") as f:
        for i in range(start, end):
            # Use flags for faster extraction
            text = doc[i].get_text(flags=flags) or ""
            f.write(json.dumps(text) + "\n")
    doc.close()
    return (start, end - start)


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


@step(requires={"pdf"}, provides={"texts"})
class ExtractText(Step):
    """Extract text from PDF pages using PyMuPDF with chunked parallel processing.

    Workers write directly to temp files to avoid IPC serialization overhead.
    Results are merged in order after all workers complete.
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

        # Create temp directory for worker output files
        temp_dir = Path(tempfile.mkdtemp(prefix="pdf_extract_"))
        chunk_files: dict[int, Path] = {}

        try:
            # Submit all chunks - each worker writes to its own temp file
            with ProcessPoolExecutor(max_workers=num_workers) as executor:
                futures = {}
                for start, end in chunks:
                    chunk_file = temp_dir / f"chunk_{start:06d}.jsonl"
                    chunk_files[start] = chunk_file
                    futures[
                        executor.submit(
                            _extract_chunk_to_file,
                            ctx.path,
                            start,
                            end,
                            str(chunk_file),
                        )
                    ] = start

                completed = 0
                for future in as_completed(futures):
                    start_idx, page_count = future.result()
                    completed += page_count
                    ctx.report_progress(
                        completed, num_pages, f"Extracted {completed}/{num_pages} pages"
                    )

            # Merge chunk files in order by direct file concatenation
            # Much faster than parsing JSON - just copy bytes
            with open(ctx.texts.path, "ab") as out_file:
                for start_idx in sorted(chunk_files.keys()):
                    chunk_file = chunk_files[start_idx]
                    with open(chunk_file, "rb") as in_file:
                        shutil.copyfileobj(in_file, out_file)

            ctx.texts._count = num_pages
            ctx.texts.finalize()

        finally:
            # Cleanup temp files
            for chunk_file in chunk_files.values():
                if chunk_file.exists():
                    chunk_file.unlink()
            if temp_dir.exists():
                temp_dir.rmdir()

        elapsed = time.perf_counter() - start_time
        pages_per_sec = num_pages / elapsed if elapsed > 0 else 0
        print(
            f"Extracted {num_pages} pages in {elapsed:.2f}s ({pages_per_sec:.1f} pages/sec)"
        )

        return ctx
