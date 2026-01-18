"""Extract text step with parallel processing."""

import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import partial

from pipetree import Step
from pypdf import PdfReader

from ..context import PdfContext


def _extract_page_text(pdf_path: str, page_num: int) -> tuple[int, str]:
    """Extract text from a single page. Runs in a separate process."""
    reader = PdfReader(pdf_path)
    text = reader.pages[page_num].extract_text() or ""
    return page_num, text


class ExtractTextStep(Step):
    """Extract text from PDF pages using parallel processing."""

    def run(self, ctx: PdfContext) -> PdfContext:  # type: ignore[override]
        if not ctx.pdf:
            raise ValueError("PDF not loaded")

        num_pages = ctx.total_pages
        num_cores = os.cpu_count() or 1
        pdf_path = ctx.path

        print(f"Extracting text from {num_pages} pages using {num_cores} cores...")
        start_time = time.perf_counter()

        # Use ProcessPoolExecutor for true parallelism
        extract_fn = partial(_extract_page_text, pdf_path)

        results: list[tuple[int, str]] = []
        with ProcessPoolExecutor(max_workers=num_cores) as executor:
            # Submit all tasks
            futures = {
                executor.submit(extract_fn, page_num): page_num
                for page_num in range(num_pages)
            }

            # Collect results and report progress as they complete
            for i, future in enumerate(as_completed(futures)):
                result = future.result()
                results.append(result)
                ctx.report_progress(i + 1, num_pages, f"Extracted page {result[0] + 1}")

        # Sort by page number and extract texts
        results.sort(key=lambda x: x[0])
        ctx.texts = [text for _, text in results]

        elapsed = time.perf_counter() - start_time
        pages_per_sec = num_pages / elapsed if elapsed > 0 else 0
        print(
            f"Extracted {num_pages} pages in {elapsed:.2f}s ({pages_per_sec:.1f} pages/sec)"
        )

        return ctx
