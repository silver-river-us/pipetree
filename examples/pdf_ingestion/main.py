"""
PDF Ingestion Pipeline Example

This example demonstrates how to build a PDF ingestion pipeline
using the pipetree framework with parallel text extraction.

Features:
- Automatic CPU core detection
- Parallel text extraction using all available cores
- Memory-efficient page-by-page processing
- Progress reporting to CSV file for real-time monitoring
- Live progress display from CSV watcher
- Output to text file
"""

import asyncio
import csv
import sys
import time
from pathlib import Path
from threading import Event, Thread

from pipetree import FileProgressNotifier, Pipetree

from .capabilities import LOAD_PDF, SAVE_TEXT, TEXT_EXTRACTION
from .context import PdfContext
from .steps import ExtractTextStep, LoadPdfStep, SaveTextStep


def create_pipeline(progress_file: Path | None = None) -> Pipetree:
    """Create the PDF ingestion pipeline."""
    notifier = FileProgressNotifier(progress_file) if progress_file else None

    return Pipetree(
        steps=[
            LoadPdfStep(LOAD_PDF, "load_pdf"),
            ExtractTextStep(TEXT_EXTRACTION, "extract_text"),
            SaveTextStep(SAVE_TEXT, "save_text"),
        ],
        progress_notifier=notifier,
    )


def watch_progress_file(path: Path, stop_event: Event) -> None:
    """Watch progress CSV and print updates to console."""
    # Wait for file to be created
    while not path.exists() and not stop_event.is_set():
        time.sleep(0.01)

    if stop_event.is_set():
        return

    # Small delay to ensure file is ready
    time.sleep(0.05)

    fieldnames = [
        "timestamp", "step_name", "step_index", "total_steps",
        "event_type", "duration_s", "error", "current", "total", "message"
    ]

    last_progress_line = ""
    with open(path, "r", encoding="utf-8") as f:
        # Skip header line
        f.readline()

        while not stop_event.is_set():
            line = f.readline()
            if not line:
                time.sleep(0.01)
                continue

            # Parse the CSV line
            try:
                values = next(csv.reader([line.strip()]))
                if len(values) < len(fieldnames):
                    continue
                row = dict(zip(fieldnames, values))

                event_type = row.get("event_type", "")
                step_name = row.get("step_name", "")

                if event_type == "started":
                    # Clear progress line and print step started
                    if last_progress_line:
                        sys.stdout.write("\r" + " " * len(last_progress_line) + "\r")
                        last_progress_line = ""
                    print(f"[{step_name}] Started")

                elif event_type == "completed":
                    # Clear progress line and print step completed
                    if last_progress_line:
                        sys.stdout.write("\r" + " " * len(last_progress_line) + "\r")
                        last_progress_line = ""
                    duration = row.get("duration_s", "")
                    if duration:
                        print(f"[{step_name}] Completed in {float(duration):.2f}s")
                    else:
                        print(f"[{step_name}] Completed")

                elif event_type == "failed":
                    if last_progress_line:
                        sys.stdout.write("\r" + " " * len(last_progress_line) + "\r")
                        last_progress_line = ""
                    error = row.get("error", "unknown error")
                    print(f"[{step_name}] FAILED: {error}")

                elif event_type == "progress":
                    current = row.get("current", "")
                    total = row.get("total", "")

                    if current and total:
                        pct = int(current) / int(total) * 100
                        bar_width = 30
                        filled = int(bar_width * int(current) / int(total))
                        bar = "=" * filled + "-" * (bar_width - filled)

                        progress_line = f"[{step_name}] [{bar}] {pct:5.1f}% ({current}/{total})"

                        sys.stdout.write("\r" + progress_line)
                        sys.stdout.flush()
                        last_progress_line = progress_line

            except (StopIteration, ValueError, KeyError, IndexError):
                continue

        # Clear any remaining progress line
        if last_progress_line:
            sys.stdout.write("\r" + " " * len(last_progress_line) + "\r")
            sys.stdout.flush()


async def main() -> None:
    """Run the PDF ingestion pipeline."""
    # Configuration - resolve paths relative to this script's directory
    script_dir = Path(__file__).parent
    pdf_path = script_dir / "small_parts.pdf"
    output_path = script_dir / (pdf_path.stem + ".txt")
    progress_path = script_dir / "progress.csv"

    print("PDF Text Extraction Pipeline")
    print("============================")
    print(f"Input:    {pdf_path}")
    print(f"Output:   {output_path}")
    print()

    # Start progress watcher in background thread
    stop_event = Event()
    watcher_thread = Thread(target=watch_progress_file, args=(progress_path, stop_event))
    watcher_thread.start()

    # Create pipeline and context
    pipeline = create_pipeline(progress_file=progress_path)
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

    except Exception as e:
        stop_event.set()
        watcher_thread.join(timeout=1.0)
        raise

    finally:
        # Close the notifier to flush the file
        if pipeline._notifier:
            pipeline._notifier.close()


if __name__ == "__main__":
    asyncio.run(main())
