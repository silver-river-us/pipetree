"""Extract text step with parallel processing."""

import time
from concurrent.futures import ProcessPoolExecutor
from functools import partial

from pypdf import PdfReader

from pipetree import Step

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
        num_cores = ctx.num_cores
        pdf_path = ctx.path

        print(f"Extracting text from {num_pages} pages using {num_cores} cores...")
        start_time = time.perf_counter()

        # Use ProcessPoolExecutor for true parallelism
        extract_fn = partial(_extract_page_text, pdf_path)
        page_nums = list(range(num_pages))

        with ProcessPoolExecutor(max_workers=num_cores) as executor:
            results = list(executor.map(extract_fn, page_nums))

        # Sort by page number and extract texts
        results.sort(key=lambda x: x[0])
        ctx.texts = [text for _, text in results]

        elapsed = time.perf_counter() - start_time
        pages_per_sec = num_pages / elapsed if elapsed > 0 else 0
        print(f"Extracted {num_pages} pages in {elapsed:.2f}s ({pages_per_sec:.1f} pages/sec)")

        return ctx
