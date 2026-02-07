"""CLI entry point for the PDF ingestion pipeline."""

import asyncio
import time

from config import PROJECT_ROOT, settings
from infra.progress import create_notifier
from lib.context import PdfContext
from lib.pipeline import PIPELINE_NAME, create_pipeline


async def main() -> None:
    """Run the PDF ingestion pipeline."""
    pdf_path = PROJECT_ROOT / settings.pdf_path
    output_path = PROJECT_ROOT / settings.output_path
    base_url = settings.pipetree_host
    api_key = settings.pipetree_api_key

    print("PDF Processing Pipeline (DSL Version)")
    print("=" * 50)
    print(f"Input:    {pdf_path}")
    print(f"Output:   {output_path}")
    print(f"Pipetree: {base_url}")
    print()
    print("Pipeline structure:")
    print("  load_pdf -> extract_text -> categorize -> route_category")
    print("                                              |")
    print("                                   +----------+----------+")
    print("                                   |                     |")
    print("                                  ops                  parts")
    print("                                   |                     |")
    print("                             process_ops         route_parts_type")
    print("                                              +----------+----------+")
    print("                                              |                     |")
    print("                                         mechanical            electrical")
    print()

    notifier = create_notifier(PIPELINE_NAME, base_url, api_key)
    pdf_pipeline = create_pipeline(notifier)
    run_id = notifier.run_id if notifier else ""

    if notifier:
        print(f"View progress at: {base_url}/runs/{run_id}")
    else:
        print("No PIPETREE_API_KEY set - running without progress reporting")

    print()

    ctx = PdfContext(
        path=str(pdf_path),
        output_path=str(output_path),
    )

    start_time = time.perf_counter()

    try:
        result = await pdf_pipeline.run(ctx)
        total_time = time.perf_counter() - start_time

        print()
        print("--- Pipeline Complete ---")
        print(f"Pages processed: {result.total_pages}")
        print(f"Category: {result.category}")
        print(f"Total time: {total_time:.2f}s")

        if result.processed_ops:
            print(
                f"Ops results: {len(result.processed_ops.get('procedures', []))} procedures found"
            )

        if result.processed_mechanical:
            print(
                f"Mechanical: {len(result.processed_mechanical.get('torque_specs', []))} torque specs found"
            )

        if result.processed_electrical:
            print(
                f"Electrical: {len(result.processed_electrical.get('wire_gauges', []))} wire gauges found"
            )

        if run_id:
            print()
            print(f"View run at: {base_url}/runs/{run_id}")
    finally:
        if notifier:
            notifier.close()


if __name__ == "__main__":
    asyncio.run(main())
