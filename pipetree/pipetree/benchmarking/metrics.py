"""Metrics collected during benchmarking."""

from typing import Any, TypedDict


class Metrics(TypedDict, total=False):
    """Metrics collected during benchmarking."""

    wall_time_s: float
    cpu_time_s: float
    throughput_pages_s: float
    throughput_chunks_s: float
    throughput_items_s: float
    items_processed: int
    peak_mem_mb: float
    cost: float
    correctness: float
    details: dict[str, Any]
