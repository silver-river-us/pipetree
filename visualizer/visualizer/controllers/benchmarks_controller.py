"""Controller for benchmark results display."""

import os
from pathlib import Path
from typing import Any

from pipetree.infrastructure.progress.benchmark_store import BenchmarkStore


class BenchmarksController:
    """Handles benchmark results requests."""

    @classmethod
    def _get_store(cls, db_path: Path) -> BenchmarkStore | None:
        """Get a BenchmarkStore instance if the database exists."""
        if db_path.exists():
            try:
                return BenchmarkStore(db_path)
            except Exception:
                return None
        return None

    @classmethod
    def index(
        cls,
        db_path: Path,
        databases: list[dict] | None = None,
        page: int = 1,
        per_page: int = 10,
    ) -> dict[str, Any]:
        """Benchmarks list page."""
        all_benchmarks = cls._get_all_benchmarks(db_path, databases)
        total_count = len(all_benchmarks)
        total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1

        # Paginate
        start = (page - 1) * per_page
        end = start + per_page
        benchmarks = all_benchmarks[start:end]

        return {
            "template": "benchmarks.html",
            "locals": {
                "benchmarks": benchmarks,
                "db_path": str(db_path),
                "page": page,
                "per_page": per_page,
                "total_count": total_count,
                "total_pages": total_pages,
            },
        }

    @classmethod
    def _get_all_benchmarks(
        cls, db_path: Path, databases: list[dict] | None = None
    ) -> list[dict]:
        """Fetch all benchmarks across databases."""
        all_benchmarks: list[dict] = []

        db_sources: list[tuple[Path, str]] = []
        seen_paths: set[str] = set()

        if databases:
            for db in databases:
                # Look for benchmarks.db in the .data folder relative to progress.db
                db_file = Path(db["path"])
                benchmark_db = db_file.parent / "benchmarks.db"
                if benchmark_db.exists() and str(benchmark_db) not in seen_paths:
                    db_sources.append((benchmark_db, db["name"]))
                    seen_paths.add(str(benchmark_db))

        # Also check the default db_path location
        benchmark_db = db_path.parent / "benchmarks.db"
        if benchmark_db.exists() and str(benchmark_db) not in seen_paths:
            db_sources.append((benchmark_db, db_path.parent.parent.name))
            seen_paths.add(str(benchmark_db))

        for db_file, db_name in db_sources:
            try:
                store = BenchmarkStore(db_file)
                benchmarks = store.get_all_benchmarks()
                for bench in benchmarks:
                    bench["db_path"] = str(db_file)
                    bench["db_name"] = db_name
                    # Get summary stats
                    summary = store.get_summary(bench["id"])
                    bench["summary"] = summary
                    bench["impl_count"] = len(summary)
                store.close()
                all_benchmarks.extend(benchmarks)
            except Exception:
                pass

        # Sort by created_at descending
        all_benchmarks.sort(key=lambda b: b.get("created_at") or 0, reverse=True)
        return all_benchmarks

    @classmethod
    def detail(cls, benchmark_id: str, db_path: Path) -> dict[str, Any]:
        """Benchmark detail page."""
        benchmark: dict | None = None
        results: list[dict] = []
        summary: dict = {}
        implementations: list[str] = []

        store = cls._get_store(db_path)
        if store:
            try:
                benchmark = store.get_benchmark(benchmark_id)
                if benchmark:
                    results = store.get_results(benchmark_id)
                    summary = store.get_summary(benchmark_id)
                    implementations = store.get_implementations(benchmark_id)
                store.close()
            except Exception:
                pass

        return {
            "template": "benchmark_detail.html",
            "locals": {
                "benchmark": benchmark,
                "results": results,
                "summary": summary,
                "implementations": implementations,
                "benchmark_id": benchmark_id,
                "db_path": str(db_path),
                "cpu_count": os.cpu_count() or 1,
            },
        }

    @classmethod
    def list_partial(
        cls,
        db_path: Path,
        databases: list[dict] | None = None,
        page: int = 1,
        per_page: int = 10,
    ) -> dict[str, Any]:
        """HTMX partial for benchmarks list."""
        all_benchmarks = cls._get_all_benchmarks(db_path, databases)
        total_count = len(all_benchmarks)
        total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1

        # Paginate
        start = (page - 1) * per_page
        end = start + per_page
        benchmarks = all_benchmarks[start:end]

        return {
            "template": "partials/benchmarks_list.html",
            "locals": {
                "benchmarks": benchmarks,
                "db_path": str(db_path),
                "page": page,
                "per_page": per_page,
                "total_count": total_count,
                "total_pages": total_pages,
            },
        }

    @classmethod
    def get_benchmarks(
        cls, db_path: Path, databases: list[dict] | None = None
    ) -> dict[str, Any]:
        """API: Get all benchmarks."""
        benchmarks = cls._get_all_benchmarks(db_path, databases)
        return {"json": {"benchmarks": benchmarks}}

    @classmethod
    def get_benchmark_detail(cls, benchmark_id: str, db_path: Path) -> dict[str, Any]:
        """API: Get benchmark details with all results."""
        store = cls._get_store(db_path)
        if not store:
            return {"json": {"error": "Database not found"}}

        try:
            benchmark = store.get_benchmark(benchmark_id)
            if not benchmark:
                return {"json": {"error": "Benchmark not found"}}

            results = store.get_results(benchmark_id)
            summary = store.get_summary(benchmark_id)
            implementations = store.get_implementations(benchmark_id)
            store.close()

            return {
                "json": {
                    "benchmark": benchmark,
                    "results": results,
                    "summary": summary,
                    "implementations": implementations,
                }
            }
        except Exception as e:
            return {"json": {"error": str(e)}}

    @classmethod
    def delete_benchmark(cls, benchmark_id: str, db_path: Path) -> dict[str, Any]:
        """API: Delete a benchmark."""
        store = cls._get_store(db_path)
        if not store:
            return {"json": {"success": False, "error": "Database not found"}}

        try:
            success = store.delete_benchmark(benchmark_id)
            store.close()
            return {"json": {"success": success}}
        except Exception as e:
            return {"json": {"success": False, "error": str(e)}}

    @classmethod
    def get_comparison_data(cls, benchmark_id: str, db_path: Path) -> dict[str, Any]:
        """API: Get data formatted for comparison charts."""
        store = cls._get_store(db_path)
        if not store:
            return {"json": {"error": "Database not found"}}

        try:
            benchmark = store.get_benchmark(benchmark_id)
            if not benchmark:
                return {"json": {"error": "Benchmark not found"}}

            results = store.get_results(benchmark_id)
            summary = store.get_summary(benchmark_id)
            implementations = store.get_implementations(benchmark_id)
            store.close()

            # Group results by fixture
            by_fixture: dict[str, dict[str, dict]] = {}
            for result in results:
                fixture_id = result["fixture_id"]
                impl_name = result["impl_name"]
                if fixture_id not in by_fixture:
                    by_fixture[fixture_id] = {}
                by_fixture[fixture_id][impl_name] = result

            # Format for charts
            fixtures = list(by_fixture.keys())

            # Time comparison data
            time_data = {
                impl: [
                    by_fixture.get(f, {}).get(impl, {}).get("wall_time_s", 0)
                    for f in fixtures
                ]
                for impl in implementations
            }

            # Memory comparison data
            memory_data = {
                impl: [
                    by_fixture.get(f, {}).get(impl, {}).get("peak_mem_mb", 0)
                    for f in fixtures
                ]
                for impl in implementations
            }

            # Correctness comparison data
            correctness_data = {
                impl: [
                    by_fixture.get(f, {}).get(impl, {}).get("correctness", 0)
                    for f in fixtures
                ]
                for impl in implementations
            }

            # CPU time comparison data
            cpu_data = {
                impl: [
                    by_fixture.get(f, {}).get(impl, {}).get("cpu_time_s", 0)
                    for f in fixtures
                ]
                for impl in implementations
            }

            return {
                "json": {
                    "benchmark": benchmark,
                    "fixtures": fixtures,
                    "implementations": implementations,
                    "time_data": time_data,
                    "memory_data": memory_data,
                    "correctness_data": correctness_data,
                    "cpu_data": cpu_data,
                    "summary": summary,
                    "cpu_count": os.cpu_count() or 1,
                }
            }
        except Exception as e:
            return {"json": {"error": str(e)}}
