"""SQLite-based storage for benchmark results."""

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any


class BenchmarkStore:
    """
    Stores benchmark results in a SQLite database.

    Features:
    - Persistent storage of benchmark suites
    - Individual result tracking per implementation/fixture
    - Query-friendly schema for visualization
    """

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS benchmarks (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                capability TEXT NOT NULL,
                description TEXT,
                created_at REAL,
                completed_at REAL,
                status TEXT DEFAULT 'pending'
            );

            CREATE TABLE IF NOT EXISTS benchmark_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                benchmark_id TEXT NOT NULL,
                impl_name TEXT NOT NULL,
                fixture_id TEXT NOT NULL,
                wall_time_s REAL,
                cpu_time_s REAL,
                peak_mem_mb REAL,
                throughput_items_s REAL,
                items_processed INTEGER,
                correctness REAL,
                extra_metrics TEXT,
                error TEXT,
                FOREIGN KEY (benchmark_id) REFERENCES benchmarks(id)
            );

            CREATE INDEX IF NOT EXISTS idx_benchmark_results_benchmark_id
                ON benchmark_results(benchmark_id);
            CREATE INDEX IF NOT EXISTS idx_benchmark_results_impl_name
                ON benchmark_results(impl_name);
            CREATE INDEX IF NOT EXISTS idx_benchmarks_capability
                ON benchmarks(capability);
            """
        )
        self._conn.commit()

    def create_benchmark(
        self,
        name: str,
        capability: str,
        description: str | None = None,
        benchmark_id: str | None = None,
    ) -> str:
        """
        Create a new benchmark suite.

        Args:
            name: Human-readable name for the benchmark
            capability: The capability being benchmarked
            description: Optional description
            benchmark_id: Optional custom ID (generated if not provided)

        Returns:
            The benchmark ID
        """
        if self._conn is None:
            raise RuntimeError("Database not initialized")

        benchmark_id = benchmark_id or str(uuid.uuid4())
        created_at = time.time()

        self._conn.execute(
            """
            INSERT INTO benchmarks (id, name, capability, description, created_at, status)
            VALUES (?, ?, ?, ?, ?, 'running')
            """,
            (benchmark_id, name, capability, description, created_at),
        )
        self._conn.commit()
        return benchmark_id

    def add_result(
        self,
        benchmark_id: str,
        impl_name: str,
        fixture_id: str,
        wall_time_s: float | None = None,
        cpu_time_s: float | None = None,
        peak_mem_mb: float | None = None,
        throughput_items_s: float | None = None,
        items_processed: int | None = None,
        correctness: float | None = None,
        extra_metrics: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> int:
        """
        Add a benchmark result.

        Returns:
            The result ID
        """
        if self._conn is None:
            raise RuntimeError("Database not initialized")

        extra_json = json.dumps(extra_metrics) if extra_metrics else None

        cursor = self._conn.execute(
            """
            INSERT INTO benchmark_results (
                benchmark_id, impl_name, fixture_id,
                wall_time_s, cpu_time_s, peak_mem_mb,
                throughput_items_s, items_processed,
                correctness, extra_metrics, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                benchmark_id,
                impl_name,
                fixture_id,
                wall_time_s,
                cpu_time_s,
                peak_mem_mb,
                throughput_items_s,
                items_processed,
                correctness,
                extra_json,
                error,
            ),
        )
        self._conn.commit()
        return cursor.lastrowid or 0

    def complete_benchmark(
        self, benchmark_id: str, status: str = "completed"
    ) -> None:
        """Mark a benchmark as completed."""
        if self._conn is None:
            return

        self._conn.execute(
            """
            UPDATE benchmarks SET completed_at = ?, status = ?
            WHERE id = ?
            """,
            (time.time(), status, benchmark_id),
        )
        self._conn.commit()

    def get_benchmark(self, benchmark_id: str) -> dict[str, Any] | None:
        """Get benchmark details by ID."""
        if self._conn is None:
            return None

        cursor = self._conn.execute(
            "SELECT * FROM benchmarks WHERE id = ?", (benchmark_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_results(
        self,
        benchmark_id: str,
        impl_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get all results for a benchmark, optionally filtered by implementation."""
        if self._conn is None:
            return []

        if impl_name:
            cursor = self._conn.execute(
                """
                SELECT * FROM benchmark_results
                WHERE benchmark_id = ? AND impl_name = ?
                ORDER BY id
                """,
                (benchmark_id, impl_name),
            )
        else:
            cursor = self._conn.execute(
                """
                SELECT * FROM benchmark_results
                WHERE benchmark_id = ?
                ORDER BY impl_name, id
                """,
                (benchmark_id,),
            )

        results = []
        for row in cursor.fetchall():
            result = dict(row)
            # Parse extra_metrics JSON
            if result.get("extra_metrics"):
                result["extra_metrics"] = json.loads(result["extra_metrics"])
            results.append(result)
        return results

    def get_all_benchmarks(
        self, capability: str | None = None
    ) -> list[dict[str, Any]]:
        """Get all benchmarks, optionally filtered by capability."""
        if self._conn is None:
            return []

        if capability:
            cursor = self._conn.execute(
                """
                SELECT * FROM benchmarks
                WHERE capability = ?
                ORDER BY created_at DESC
                """,
                (capability,),
            )
        else:
            cursor = self._conn.execute(
                "SELECT * FROM benchmarks ORDER BY created_at DESC"
            )
        return [dict(row) for row in cursor.fetchall()]

    def get_implementations(self, benchmark_id: str) -> list[str]:
        """Get all unique implementation names for a benchmark."""
        if self._conn is None:
            return []

        cursor = self._conn.execute(
            """
            SELECT DISTINCT impl_name FROM benchmark_results
            WHERE benchmark_id = ?
            ORDER BY impl_name
            """,
            (benchmark_id,),
        )
        return [row[0] for row in cursor.fetchall()]

    def get_summary(self, benchmark_id: str) -> dict[str, Any]:
        """
        Get aggregated summary statistics for a benchmark.

        Returns average metrics per implementation.
        """
        if self._conn is None:
            return {}

        cursor = self._conn.execute(
            """
            SELECT
                impl_name,
                COUNT(*) as fixture_count,
                AVG(wall_time_s) as avg_wall_time_s,
                AVG(peak_mem_mb) as avg_peak_mem_mb,
                AVG(correctness) as avg_correctness,
                AVG(throughput_items_s) as avg_throughput,
                SUM(CASE WHEN error IS NOT NULL THEN 1 ELSE 0 END) as error_count
            FROM benchmark_results
            WHERE benchmark_id = ?
            GROUP BY impl_name
            ORDER BY avg_wall_time_s
            """,
            (benchmark_id,),
        )

        return {
            row["impl_name"]: {
                "fixture_count": row["fixture_count"],
                "avg_wall_time_s": row["avg_wall_time_s"],
                "avg_peak_mem_mb": row["avg_peak_mem_mb"],
                "avg_correctness": row["avg_correctness"],
                "avg_throughput": row["avg_throughput"],
                "error_count": row["error_count"],
            }
            for row in cursor.fetchall()
        }

    def delete_benchmark(self, benchmark_id: str) -> bool:
        """Delete a benchmark and all its results."""
        if self._conn is None:
            return False

        try:
            # Delete results first (foreign key)
            self._conn.execute(
                "DELETE FROM benchmark_results WHERE benchmark_id = ?",
                (benchmark_id,),
            )
            # Delete benchmark
            cursor = self._conn.execute(
                "DELETE FROM benchmarks WHERE id = ?",
                (benchmark_id,),
            )
            self._conn.commit()
            return cursor.rowcount > 0
        except Exception:
            return False

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
