"""HTTP-based benchmark store that sends results to a remote pipetree cloud API."""

import logging
import uuid
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class HTTPBenchmarkStore:
    """
    Sends benchmark results to a remote API via HTTP.

    Mirrors the write interface of BenchmarkStore but sends data
    to the pipetree cloud REST Ingest API instead of writing locally.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = 10.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=f"{self.base_url}/api/v1",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    def create_benchmark(
        self,
        name: str,
        capability: str,
        description: str | None = None,
        benchmark_id: str | None = None,
    ) -> str:
        """Create a new benchmark suite on the remote API."""
        benchmark_id = benchmark_id or str(uuid.uuid4())
        payload: dict[str, Any] = {
            "id": benchmark_id,
            "name": name,
            "capability": capability,
            "description": description,
        }
        try:
            resp = self._client.post("/benchmarks", json=payload)
            resp.raise_for_status()
        except httpx.HTTPError:
            logger.warning("Failed to create benchmark %s", benchmark_id, exc_info=True)
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
        """Add a benchmark result via the remote API."""
        payload: dict[str, Any] = {
            "impl_name": impl_name,
            "fixture_id": fixture_id,
            "wall_time_s": wall_time_s,
            "cpu_time_s": cpu_time_s,
            "peak_mem_mb": peak_mem_mb,
            "throughput_items_s": throughput_items_s,
            "items_processed": items_processed,
            "correctness": correctness,
            "extra_metrics": extra_metrics,
            "error": error,
        }
        try:
            resp = self._client.post(
                f"/benchmarks/{benchmark_id}/results", json=payload
            )
            resp.raise_for_status()
            result_id: int = resp.json().get("result_id", 0)
            return result_id
        except httpx.HTTPError:
            logger.warning(
                "Failed to add result for benchmark %s",
                benchmark_id,
                exc_info=True,
            )
            return 0

    def complete_benchmark(self, benchmark_id: str, status: str = "completed") -> None:
        """Mark a benchmark as completed on the remote API."""
        try:
            resp = self._client.patch(
                f"/benchmarks/{benchmark_id}", json={"status": status}
            )
            resp.raise_for_status()
        except httpx.HTTPError:
            logger.warning(
                "Failed to complete benchmark %s", benchmark_id, exc_info=True
            )

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()
