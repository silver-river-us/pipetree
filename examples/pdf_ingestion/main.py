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
import time
from pathlib import Path

from pipetree import Pipetree

from .capabilities import LOAD_PDF, SAVE_TEXT, TEXT_EXTRACTION
from .context import PdfContext
from .steps import ExtractTextStep, LoadPdfStep, SaveTextStep


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
    # Configuration - resolve paths relative to this script's directory
    script_dir = Path(__file__).parent
    pdf_path = script_dir / "small_parts.pdf"
    output_path = script_dir / (pdf_path.stem + ".txt")

    print(f"PDF Text Extraction Pipeline")
    print(f"============================")
    print(f"Input:  {pdf_path}")
    print(f"Output: {output_path}")
    print()

    # Create pipeline and context
    pipeline = create_pipeline()
    ctx = PdfContext(
        path=str(pdf_path),
        output_path=str(output_path),
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
