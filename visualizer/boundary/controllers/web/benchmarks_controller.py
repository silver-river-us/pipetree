"""Benchmarks web controller."""

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse

from lib import benchmarks as benchmarks_lib
from lib.exceptions import BenchmarkNotFoundError, DatabaseNotFoundError

from boundary.base.http_context import get_db_path, get_template_context, require_login
from boundary.base.templates import templates

router = APIRouter()


@router.get("/benchmarks", response_class=HTMLResponse)
async def benchmarks_index(
    request: Request,
    db: str = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=100),
):
    """Benchmarks list page."""
    if redirect := require_login(request):
        return redirect

    db_path = get_db_path(db, request)
    databases: list[dict] = []
    all_benchmarks = benchmarks_lib.get_all_benchmarks(db_path, databases)
    total_count = len(all_benchmarks)
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
    start = (page - 1) * per_page
    end = start + per_page
    benchmarks = all_benchmarks[start:end]

    return templates().TemplateResponse(
        request,
        "benchmarks.html",
        {
            "benchmarks": benchmarks,
            "db_path": str(db_path),
            "page": page,
            "per_page": per_page,
            "total_count": total_count,
            "total_pages": total_pages,
            **get_template_context(db_path),
        },
    )


@router.get("/benchmarks/{benchmark_id}", response_class=HTMLResponse)
async def benchmark_detail(
    request: Request, benchmark_id: str, db: str = Query(default=None)
):
    """Benchmark detail page."""
    if redirect := require_login(request):
        return redirect

    db_path = get_db_path(db, request)

    try:
        data = benchmarks_lib.get_benchmark_detail(benchmark_id, db_path)
    except (DatabaseNotFoundError, BenchmarkNotFoundError):
        data = None

    return templates().TemplateResponse(
        request,
        "benchmark_detail.html",
        {
            "benchmark": data["benchmark"] if data else None,
            "results": data["results"] if data else [],
            "summary": data["summary"] if data else {},
            "implementations": data["implementations"] if data else [],
            "benchmark_id": benchmark_id,
            "db_path": str(db_path),
            "cpu_count": data["cpu_count"] if data else 1,
            **get_template_context(db_path),
        },
    )
