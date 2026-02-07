"""HTTP-based progress notifier that sends events to a remote visualizer API."""

import logging
import time
import uuid
from typing import Any

import httpx

from pipetree.infrastructure.progress.progress_notifier import (
    ProgressEvent,
    ProgressNotifier,
)

logger = logging.getLogger(__name__)


class HTTPProgressNotifier(ProgressNotifier):
    """
    Sends progress events to a remote visualizer via HTTP POST.

    Mirrors the SQLiteProgressNotifier interface but sends data
    to the visualizer's REST Ingest API instead of writing locally.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        pipeline: str,
        run_id: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.pipeline = pipeline
        self.run_id = run_id or str(uuid.uuid4())
        self._client = httpx.Client(
            base_url=f"{self.base_url}/api/v1",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    def register_run(
        self, name: str, step_names: list[str], started_at: float | None = None
    ) -> str:
        """Register a new pipeline run with the remote visualizer."""
        payload: dict[str, Any] = {
            "id": self.run_id,
            "pipeline": name,
            "step_names": step_names,
            "started_at": started_at or time.time(),
        }
        try:
            resp = self._client.post("/runs", json=payload)
            resp.raise_for_status()
        except httpx.HTTPError:
            logger.warning("Failed to register run %s", self.run_id, exc_info=True)
        return self.run_id

    def register_branch(
        self,
        parent_step: str,
        branch_name: str,
        step_names: list[str],
        start_index: int,
    ) -> None:
        """Register a branch with the remote visualizer."""
        payload = {
            "parent_step": parent_step,
            "branch_name": branch_name,
            "step_names": step_names,
            "start_index": start_index,
        }
        try:
            resp = self._client.post(f"/runs/{self.run_id}/branches", json=payload)
            resp.raise_for_status()
        except httpx.HTTPError:
            logger.warning(
                "Failed to register branch %s for run %s",
                branch_name,
                self.run_id,
                exc_info=True,
            )

    def complete_run(self, status: str = "completed") -> None:
        """Mark the run as completed on the remote visualizer."""
        try:
            resp = self._client.patch(f"/runs/{self.run_id}", json={"status": status})
            resp.raise_for_status()
        except httpx.HTTPError:
            logger.warning("Failed to complete run %s", self.run_id, exc_info=True)

    def notify(self, event: ProgressEvent) -> None:
        """Send a progress event to the remote visualizer."""
        payload = {
            "events": [
                {
                    "step_name": event.step_name,
                    "step_index": event.step_index,
                    "total_steps": event.total_steps,
                    "event_type": event.event_type,
                    "duration_s": event.duration_s,
                    "cpu_time_s": event.cpu_time_s,
                    "peak_mem_mb": event.peak_mem_mb,
                    "error": event.error,
                    "current": event.current,
                    "total": event.total,
                    "message": event.message,
                    "timestamp": event.timestamp,
                }
            ]
        }
        try:
            resp = self._client.post(f"/runs/{self.run_id}/events", json=payload)
            resp.raise_for_status()
        except httpx.HTTPError:
            logger.warning(
                "Failed to send event for run %s step %s",
                self.run_id,
                event.step_name,
                exc_info=True,
            )

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()
