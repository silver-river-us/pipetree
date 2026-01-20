"""
PDF Ingestion Pipeline Example - DSL Version

This example demonstrates the clean DSL syntax for defining pipelines.
The pipeline structure is immediately visible:

    LoadPdf
    ExtractText
    Categorize
    category >> [
        ops >> ProcessOps,
        parts >> parts_type >> [
            mechanical >> ProcessMechanical,
            electrical >> ProcessElectrical,
        ],
    ]
    SaveText
"""

import asyncio
import time
from pathlib import Path

from pipetree import (
    B,
    SQLiteProgressNotifier,
    SQLiteProgressWatcher,
    pipeline,
    route,
)

from .context import PdfContext
from .steps import (
    Categorize,
    ExtractText,
    LoadPdf,
    ProcessElectrical,
    ProcessMechanical,
    ProcessOps,
    SaveText,
)

# =============================================================================
# Route markers - define once, use in pipeline
# =============================================================================

category = route("category", default="ops")
parts_type = route("parts_type", default="mechanical")

# Branch markers - for explicit branch assignment
ops = B("ops")
parts = B("parts")
mechanical = B("mechanical")
electrical = B("electrical")


# =============================================================================
# Pipeline definition - the tree structure is immediately visible!
# =============================================================================


def create_pipeline(
    db_path: Path | None = None,
) -> tuple[any, SQLiteProgressNotifier | None]:
    """Create the PDF ingestion pipeline with nested branching."""
    notifier = SQLiteProgressNotifier(db_path) if db_path else None

    pdf_pipeline = pipeline(
        "PDF Processing Pipeline",
        [
            LoadPdf,
            ExtractText,
            Categorize,
            category
            >> [
                ops >> ProcessOps,
                parts
                >> parts_type
                >> [
                    mechanical >> ProcessMechanical,
                    electrical >> ProcessElectrical,
                ],
            ],
            SaveText,
        ],
        progress_notifier=notifier,
    )

    return pdf_pipeline, notifier


# =============================================================================
# Main entry point
# =============================================================================


async def main() -> None:
    """Run the PDF ingestion pipeline."""
    project_root = Path(__file__).parent.parent
    pdf_path = project_root / "assets" / "big.pdf"
    output_path = project_root / "assets" / (pdf_path.stem + ".txt")
    db_path = project_root / "db" / "progress.db"

    print("PDF Processing Pipeline (DSL Version)")
    print("=" * 50)
    print(f"Input:    {pdf_path}")
    print(f"Output:   {output_path}")
    print(f"Database: {db_path}")
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
    print("View progress at: http://localhost:8000")
    print()

    # Create pipeline
    pdf_pipeline, notifier = create_pipeline(db_path=db_path)
    run_id = notifier.run_id if notifier else ""

    # Start progress watcher
    watcher = SQLiteProgressWatcher(db_path, run_id)
    watcher.start()

    ctx = PdfContext(
        path=str(pdf_path),
        output_path=str(output_path),
    )

    # Run the pipeline
    start_time = time.perf_counter()
    try:
        result = await pdf_pipeline.run(ctx)
        total_time = time.perf_counter() - start_time

        watcher.stop()

        # Summary
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
        print()
        print(f"View run at: http://localhost:8000/runs/{run_id}?db={db_path}")

    except Exception:
        watcher.stop()
        raise

    finally:
        if notifier:
            notifier.close()


if __name__ == "__main__":
    asyncio.run(main())
