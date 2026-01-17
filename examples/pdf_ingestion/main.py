"""
PDF Ingestion Pipeline Example

This example demonstrates how to build a PDF ingestion pipeline
using the ingestion framework with typed context.
"""

import asyncio

from pipetree import Pipetree

from .capabilities import CHUNKING, LOAD_PDF, PAGE_EXTRACTION, TEXT_EXTRACTION
from .context import PdfContext
from .steps import ChunkTextStep, ExtractPagesStep, ExtractTextStep, LoadPdfStep


def create_pipeline() -> Pipetree:
    """Create the PDF ingestion pipeline."""
    return Pipetree(
        steps=[
            LoadPdfStep(LOAD_PDF, "load_pdf"),
            ExtractPagesStep(PAGE_EXTRACTION, "extract_pages"),
            ExtractTextStep(TEXT_EXTRACTION, "extract_text"),
            ChunkTextStep(CHUNKING, "chunk_text", chunk_size=500),
        ]
    )


async def main() -> None:
    """Run the PDF ingestion pipeline."""
    pipeline = create_pipeline()

    # Create typed context with initial data
    ctx = PdfContext(path="WORKSHOP_MANUAL_TB335R.pdf")

    # Run the pipeline
    result = await pipeline.run(ctx)

    print("\n--- Pipeline Complete ---")
    print(f"Chunks created: {len(result.chunks)}")
    for chunk in result.chunks:
        print(f"  - {chunk['id']}: {chunk['text'][:50]}...")


if __name__ == "__main__":
    asyncio.run(main())
