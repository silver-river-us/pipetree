"""
PDF Ingestion Pipeline Example

This example demonstrates how to build a PDF ingestion pipeline
using the pipetree framework with parallel text extraction and nested branching.

Features:
- Automatic CPU core detection
- Parallel text extraction using all available cores
- Document categorization (ops vs parts)
- Nested branching: parts -> mechanical/electrical
- Progress reporting to SQLite for real-time monitoring
- Web visualizer at http://localhost:8000
"""

import asyncio
import time
from pathlib import Path
from threading import Event, Thread

from pipetree import Pipetree, SQLiteProgressNotifier

from .capabilities import (
    CATEGORIZE,
    LOAD_PDF,
    PROCESS_ELECTRICAL,
    PROCESS_MECHANICAL,
    PROCESS_OPS,
    ROUTE_BY_CATEGORY,
    ROUTE_PARTS_TYPE,
    SAVE_TEXT,
    TEXT_EXTRACTION,
)
from .context import PdfContext
from .steps import (
    CategorizeStep,
    CategoryRouter,
    ExtractTextStep,
    LoadPdfStep,
    PartsTypeRouter,
    ProcessElectricalStep,
    ProcessMechanicalStep,
    ProcessOpsStep,
    SaveTextStep,
)
from .watch import watch_sqlite_progress


def create_pipeline(
    db_path: Path | None = None,
) -> tuple[Pipetree, SQLiteProgressNotifier | None]:
    """Create the PDF ingestion pipeline with nested branching."""
    notifier = SQLiteProgressNotifier(db_path) if db_path else None

    pipeline = Pipetree(
        steps=[
            LoadPdfStep(LOAD_PDF, "load_pdf"),
            ExtractTextStep(TEXT_EXTRACTION, "extract_text"),
            CategorizeStep(CATEGORIZE, "categorize"),
            CategoryRouter(
                cap=ROUTE_BY_CATEGORY,
                name="route_by_category",
                table={
                    "ops": ProcessOpsStep(PROCESS_OPS, "process_ops"),
                    "parts": PartsTypeRouter(
                        cap=ROUTE_PARTS_TYPE,
                        name="route_parts_type",
                        table={
                            "mechanical": ProcessMechanicalStep(
                                PROCESS_MECHANICAL, "process_mechanical"
                            ),
                            "electrical": ProcessElectricalStep(
                                PROCESS_ELECTRICAL, "process_electrical"
                            ),
                        },
                        default="mechanical",
                    ),
                },
                default="ops",
            ),
            SaveTextStep(SAVE_TEXT, "save_text"),
        ],
        progress_notifier=notifier,
        name="PDF Processing Pipeline",
    )

    # Register branches with the notifier
    if notifier:
        # Register the two top-level branches
        notifier.register_branch(
            parent_step="route_by_category",
            branch_name="ops",
            step_names=["process_ops"],
            start_index=4,
        )
        notifier.register_branch(
            parent_step="route_by_category",
            branch_name="parts",
            step_names=["route_parts_type"],
            start_index=4,
        )
        # Register nested branches under parts
        notifier.register_branch(
            parent_step="route_parts_type",
            branch_name="mechanical",
            step_names=["process_mechanical"],
            start_index=5,
        )
        notifier.register_branch(
            parent_step="route_parts_type",
            branch_name="electrical",
            step_names=["process_electrical"],
            start_index=5,
        )

    return pipeline, notifier


async def main() -> None:
    """Run the PDF ingestion pipeline."""
    # Configuration - resolve paths relative to project root (1 level up from pdf_ingestion/)
    project_root = Path(__file__).parent.parent
    pdf_path = project_root / "assets" / "big.pdf"
    output_path = project_root / "assets" / (pdf_path.stem + ".txt")
    db_path = project_root / "db" / "progress.db"

    print("PDF Processing Pipeline (with Nested Branching)")
    print("================================================")
    print(f"Input:    {pdf_path}")
    print(f"Output:   {output_path}")
    print(f"Database: {db_path}")
    print()
    print("Pipeline structure:")
    print("  load_pdf -> extract_text -> categorize -> route_by_category")
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

    # Create pipeline and get the run_id
    pipeline, notifier = create_pipeline(db_path=db_path)
    run_id = notifier.run_id if notifier else ""

    # Start progress watcher in background thread
    stop_event = Event()
    watcher_thread = Thread(
        target=watch_sqlite_progress, args=(db_path, run_id, stop_event)
    )
    watcher_thread.start()

    ctx = PdfContext(
        path=str(pdf_path),
        output_path=str(output_path),
    )

    # Run the pipeline
    start_time = time.perf_counter()
    try:
        result = await pipeline.run(ctx)
        total_time = time.perf_counter() - start_time

        # Stop the watcher
        stop_event.set()
        watcher_thread.join(timeout=1.0)

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
        stop_event.set()
        watcher_thread.join(timeout=1.0)
        raise

    finally:
        # Close the notifier
        if notifier:
            notifier.close()


if __name__ == "__main__":
    asyncio.run(main())
