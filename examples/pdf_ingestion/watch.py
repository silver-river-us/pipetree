"""SQLite progress watcher for console output."""

import sqlite3
import sys
import time
from pathlib import Path
from threading import Event


def watch_sqlite_progress(db_path: Path, run_id: str, stop_event: Event) -> None:
    """Watch SQLite database and print updates to console."""
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
