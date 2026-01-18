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
import sys
import time
from pathlib import Path
from threading import Event, Thread

from pipetree import Capability, Pipetree, SQLiteProgressNotifier

from .capabilities import (
    CATEGORIZE,
    LOAD_PDF,
    PROCESS_ELECTRICAL,
    PROCESS_MECHANICAL,
    PROCESS_OPS,
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


def create_pipeline(db_path: Path | None = None) -> tuple[Pipetree, SQLiteProgressNotifier | None]:
    """Create the PDF ingestion pipeline with nested branching."""
    notifier = SQLiteProgressNotifier(db_path) if db_path else None

    # Nested router capability for parts -> mechanical/electrical
    PARTS_ROUTER_CAP = Capability(
        name="route_parts_type",
        requires={"texts", "category"},
        provides={"processed_mechanical", "processed_electrical", "processed_parts"},
    )

    # Create the nested router for parts type
    parts_type_router = PartsTypeRouter(
        cap=PARTS_ROUTER_CAP,
        name="route_parts_type",
        table={
            "mechanical": ProcessMechanicalStep(PROCESS_MECHANICAL, "process_mechanical"),
            "electrical": ProcessElectricalStep(PROCESS_ELECTRICAL, "process_electrical"),
        },
        default="mechanical",
    )

    # Top-level router capability
    ROUTER_CAP = Capability(
        name="process_document",
        requires={"texts", "category"},
        provides={"processed_ops", "processed_parts", "processed_mechanical", "processed_electrical"},
    )

    # Create the top-level router with branch steps
    category_router = CategoryRouter(
        cap=ROUTER_CAP,
        name="route_by_category",
        table={
            "ops": ProcessOpsStep(PROCESS_OPS, "process_ops"),
            "parts": parts_type_router,  # Nested router!
        },
        default="ops",
    )

    pipeline = Pipetree(
        steps=[
            LoadPdfStep(LOAD_PDF, "load_pdf"),
            ExtractTextStep(TEXT_EXTRACTION, "extract_text"),
            CategorizeStep(CATEGORIZE, "categorize"),
            category_router,
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


def watch_sqlite_progress(db_path: Path, run_id: str, stop_event: Event) -> None:
    """Watch SQLite database and print updates to console."""
    import sqlite3

    # Wait for database to be created
    while not db_path.exists() and not stop_event.is_set():
        time.sleep(0.01)

    if stop_event.is_set():
        return

    time.sleep(0.05)

    last_event_id = 0
    last_progress_line = ""

    while not stop_event.is_set():
        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row

            # Get new events
            cursor = conn.execute(
                """
                SELECT * FROM events
                WHERE run_id = ? AND id > ?
                ORDER BY id
                """,
                (run_id, last_event_id),
            )
            events = [dict(row) for row in cursor.fetchall()]

            for event in events:
                last_event_id = event["id"]
                event_type = event["event_type"]
                step_name = event["step_name"]

                if event_type == "started":
                    if last_progress_line:
                        sys.stdout.write("\r" + " " * len(last_progress_line) + "\r")
                        last_progress_line = ""
                    print(f"[{step_name}] Started")

                elif event_type == "completed":
                    if last_progress_line:
                        sys.stdout.write("\r" + " " * len(last_progress_line) + "\r")
                        last_progress_line = ""
                    duration = event.get("duration_s")
                    if duration:
                        print(f"[{step_name}] Completed in {duration:.2f}s")
                    else:
                        print(f"[{step_name}] Completed")

                elif event_type == "failed":
                    if last_progress_line:
                        sys.stdout.write("\r" + " " * len(last_progress_line) + "\r")
                        last_progress_line = ""
                    error = event.get("error", "unknown error")
                    print(f"[{step_name}] FAILED: {error}")

                elif event_type == "progress":
                    current = event.get("current")
                    total = event.get("total")

                    if current is not None and total is not None and total > 0:
                        pct = current / total * 100
                        bar_width = 30
                        filled = int(bar_width * current / total)
                        bar = "=" * filled + "-" * (bar_width - filled)

                        progress_line = f"[{step_name}] [{bar}] {pct:5.1f}% ({current}/{total})"

                        sys.stdout.write("\r" + progress_line)
                        sys.stdout.flush()
                        last_progress_line = progress_line

            conn.close()

        except Exception:
            pass

        time.sleep(0.05)

    # Clear any remaining progress line
    if last_progress_line:
        sys.stdout.write("\r" + " " * len(last_progress_line) + "\r")
        sys.stdout.flush()


async def main() -> None:
    """Run the PDF ingestion pipeline."""
    # Configuration - resolve paths relative to this script's directory
    script_dir = Path(__file__).parent
    pdf_path = script_dir / "small.pdf"
    output_path = script_dir / (pdf_path.stem + ".txt")
    db_path = script_dir / "progress.db"

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
    watcher_thread = Thread(target=watch_sqlite_progress, args=(db_path, run_id, stop_event))
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
            print(f"Ops results: {len(result.processed_ops.get('procedures', []))} procedures found")
        if result.processed_mechanical:
            print(f"Mechanical: {len(result.processed_mechanical.get('torque_specs', []))} torque specs found")
        if result.processed_electrical:
            print(f"Electrical: {len(result.processed_electrical.get('wire_gauges', []))} wire gauges found")
        print()
        print(f"View run at: http://localhost:8000/runs/{run_id}?db={db_path}")

    except Exception as e:
        stop_event.set()
        watcher_thread.join(timeout=1.0)
        raise

    finally:
        # Close the notifier
        if notifier:
            notifier.close()


if __name__ == "__main__":
    asyncio.run(main())
