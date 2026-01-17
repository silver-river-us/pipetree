"""
PDF Ingestion Pipeline Example

This example demonstrates how to build a PDF ingestion pipeline
using the pipetree framework with parallel text extraction.

Features:
- Automatic CPU core detection
- Parallel text extraction using all available cores
- Memory-efficient page-by-page processing
- Progress reporting to SQLite for real-time monitoring
- Web visualizer at http://localhost:8000
- Output to text file
"""

import asyncio
import sys
import time
from pathlib import Path
from threading import Event, Thread

from pipetree import Pipetree, SQLiteProgressNotifier

from .capabilities import LOAD_PDF, SAVE_TEXT, TEXT_EXTRACTION
from .context import PdfContext
from .steps import ExtractTextStep, LoadPdfStep, SaveTextStep


def create_pipeline(db_path: Path | None = None) -> tuple[Pipetree, SQLiteProgressNotifier | None]:
    """Create the PDF ingestion pipeline."""
    notifier = SQLiteProgressNotifier(db_path) if db_path else None

    pipeline = Pipetree(
        steps=[
            LoadPdfStep(LOAD_PDF, "load_pdf"),
            ExtractTextStep(TEXT_EXTRACTION, "extract_text"),
            SaveTextStep(SAVE_TEXT, "save_text"),
        ],
        progress_notifier=notifier,
        name="PDF Text Extraction",
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
    pdf_path = script_dir / "big.pdf"
    output_path = script_dir / (pdf_path.stem + ".txt")
    db_path = script_dir / "progress.db"

    print("PDF Text Extraction Pipeline")
    print("============================")
    print(f"Input:    {pdf_path}")
    print(f"Output:   {output_path}")
    print(f"Database: {db_path}")
    print()
    print("View progress at: http://localhost:8000")
    print("(Run: pipenv run python -m visualizer.app)")
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
        print(f"Total time: {total_time:.2f}s")
        print(f"Output saved to: {result.output_path}")
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
