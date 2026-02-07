"""Benchmarks API controller."""

from pathlib import Path

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from boundary.base.http_context import get_db_path
from boundary.base.templates import templates
from lib import benchmarks as benchmarks_lib
from lib.exceptions import BenchmarkNotFoundError, DatabaseNotFoundError

router = APIRouter(prefix="/benchmarks")


@router.get("")
async def api_benchmarks_list(
    request: Request,
    db: str = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=100),
):
    """HTMX partial for benchmarks list."""
    databases: list[dict] = []
    db_path = get_db_path(db, request)
    all_benchmarks = benchmarks_lib.get_all_benchmarks(db_path, databases)
    total_count = len(all_benchmarks)
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
    start = (page - 1) * per_page
    end = start + per_page
    benchmarks = all_benchmarks[start:end]

    return templates().TemplateResponse(
        request,
        "partials/benchmarks_list.html",
        {
            "benchmarks": benchmarks,
            "db_path": str(db_path),
            "page": page,
            "per_page": per_page,
            "total_count": total_count,
            "total_pages": total_pages,
        },
    )


@router.get("/json")
async def api_benchmarks_json(request: Request, db: str = Query(default=None)):
    """Get list of all benchmarks as JSON."""
    databases: list[dict] = []
    benchmarks = benchmarks_lib.get_all_benchmarks(get_db_path(db, request), databases)
    return JSONResponse(content={"benchmarks": benchmarks})


@router.get("/{benchmark_id}")
async def api_benchmark_detail(
    request: Request, benchmark_id: str, db: str = Query(default=None)
):
    """Get benchmark details with all results."""
    try:
        data = benchmarks_lib.get_benchmark_detail(benchmark_id, get_db_path(db, request))
    except (DatabaseNotFoundError, BenchmarkNotFoundError):
        return JSONResponse(content={"error": "Not found"}, status_code=404)

    return JSONResponse(content=data)


@router.get("/{benchmark_id}/comparison")
async def api_benchmark_comparison(
    request: Request, benchmark_id: str, db: str = Query(default=None)
):
    """Get benchmark data formatted for comparison charts."""
    try:
        data = benchmarks_lib.get_comparison_data(benchmark_id, get_db_path(db, request))
    except (DatabaseNotFoundError, BenchmarkNotFoundError):
        return JSONResponse(content={"error": "Not found"}, status_code=404)

    return JSONResponse(content=data)


@router.delete("/{benchmark_id}")
async def api_benchmark_delete(
    request: Request, benchmark_id: str, db: str = Query(...)
):
    """Delete a benchmark."""
    try:
        benchmarks_lib.delete_benchmark(benchmark_id, Path(db))
        return JSONResponse(content={"success": True})
    except DatabaseNotFoundError:
        return JSONResponse(content={"success": False, "error": "Database not found"})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)})
