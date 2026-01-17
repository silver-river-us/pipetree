"""
PDF Ingestion Pipeline Example

This example demonstrates how to build a PDF ingestion pipeline
using the pipetree framework with parallel text extraction.

Features:
- Automatic CPU core detection
- Parallel text extraction using all available cores
- Memory-efficient page-by-page processing
- Output to text file
"""

import asyncio
import os
import time
from pathlib import Path

from pipetree import Pipetree

from .capabilities import LOAD_PDF, SAVE_TEXT, TEXT_EXTRACTION
from .context import PdfContext
from .steps import ExtractTextStep, LoadPdfStep, SaveTextStep


def get_cpu_count() -> int:
    """Get the number of available CPU cores."""
    # Try to get the number of CPUs available to this process
    try:
        return len(os.sched_getaffinity(0))
    except AttributeError:
        # sched_getaffinity not available on all platforms
        pass

    # Fall back to os.cpu_count()
    count = os.cpu_count()
    return count if count else 1


def create_pipeline() -> Pipetree:
    """Create the PDF ingestion pipeline."""
    return Pipetree(
        steps=[
            LoadPdfStep(LOAD_PDF, "load_pdf"),
            ExtractTextStep(TEXT_EXTRACTION, "extract_text"),
            SaveTextStep(SAVE_TEXT, "save_text"),
        ]
    )


async def main() -> None:
    """Run the PDF ingestion pipeline."""
    # Configuration
    pdf_path = "WORKSHOP_MANUAL_TB335R.pdf"
    output_path = Path(pdf_path).stem + ".txt"
    num_cores = get_cpu_count()

    print(f"PDF Text Extraction Pipeline")
    print(f"============================")
    print(f"Input:  {pdf_path}")
    print(f"Output: {output_path}")
    print(f"Cores:  {num_cores}")
    print()

    # Create pipeline and context
    pipeline = create_pipeline()
    ctx = PdfContext(
        path=pdf_path,
        output_path=output_path,
        num_cores=num_cores,
    )

    # Run the pipeline
    start_time = time.perf_counter()
    result = await pipeline.run(ctx)
    total_time = time.perf_counter() - start_time

    # Summary
    print()
    print(f"--- Pipeline Complete ---")
    print(f"Pages processed: {result.total_pages}")
    print(f"Total time: {total_time:.2f}s")
    print(f"Output saved to: {result.output_path}")


if __name__ == "__main__":
    asyncio.run(main())
