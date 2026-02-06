"""WebSocket controller for real-time updates."""

import asyncio
import contextlib
from pathlib import Path

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from pipetree.infrastructure.progress.models import Event, Run, Step, get_session
from sqlmodel import select

from boundary.base.http_context import get_db_path

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections for live updates."""

    def __init__(self) -> None:
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, run_id: str) -> None:
        await websocket.accept()
        if run_id not in self.active_connections:
            self.active_connections[run_id] = []
        self.active_connections[run_id].append(websocket)

    def disconnect(self, websocket: WebSocket, run_id: str) -> None:
        if (
            run_id in self.active_connections
            and websocket in self.active_connections[run_id]
        ):
            self.active_connections[run_id].remove(websocket)
            if not self.active_connections[run_id]:
                del self.active_connections[run_id]

    async def broadcast(self, run_id: str, message: dict) -> None:
        if run_id in self.active_connections:
            for connection in self.active_connections[run_id]:
                with contextlib.suppress(Exception):
                    await connection.send_json(message)


manager = ConnectionManager()


@router.websocket("/ws/benchmark/{benchmark_id}")
async def websocket_benchmark_endpoint(
    websocket: WebSocket, benchmark_id: str, db: str = Query(default=None)
):
    """WebSocket endpoint for real-time benchmark updates."""
    from pipetree.infrastructure.progress.benchmark_store import BenchmarkStore

    if db:
        db_path = Path(db)
        if db_path.name == "benchmarks.db":
            benchmark_db = db_path
        else:
            benchmark_db = db_path.parent / "benchmarks.db"
    else:
        db_path = get_db_path(None)
        benchmark_db = db_path.parent / "benchmarks.db"

    ws_key = f"benchmark:{benchmark_id}"
    await manager.connect(websocket, ws_key)

    store = None
    try:
        last_result_count = -1
        last_status = None

        while True:
            if benchmark_db.exists():
                try:
                    if store is None:
                        store = BenchmarkStore(benchmark_db)

                    benchmark = store.get_benchmark(benchmark_id)

                    if benchmark:
                        results = store.get_results(benchmark_id)
                        current_result_count = len(results)
                        current_status = benchmark["status"]

                        if (
                            current_result_count != last_result_count
                            or current_status != last_status
                        ):
                            last_result_count = current_result_count
                            last_status = current_status
                            summary = store.get_summary(benchmark_id)
                            implementations = store.get_implementations(benchmark_id)

                            await websocket.send_json(
                                {
                                    "type": "update",
                                    "status": current_status,
                                    "result_count": current_result_count,
                                    "summary": summary,
                                    "implementations": implementations,
                                }
                            )

                        if current_status in ("completed", "failed"):
                            await websocket.send_json(
                                {
                                    "type": "complete",
                                    "status": current_status,
                                    "completed_at": benchmark.get("completed_at"),
                                }
                            )
                            break

                except Exception as e:
                    await websocket.send_json({"type": "error", "message": str(e)})
                    # Reset store on error so next iteration creates a fresh one
                    if store:
                        with contextlib.suppress(Exception):
                            store.close()
                        store = None

            await asyncio.sleep(0.5)

    except WebSocketDisconnect:
        pass
    finally:
        if store:
            with contextlib.suppress(Exception):
                store.close()
        manager.disconnect(websocket, ws_key)


@router.websocket("/ws/{run_id}")
async def websocket_endpoint(
    websocket: WebSocket, run_id: str, db: str = Query(default=None)
):
    """WebSocket endpoint for real-time updates."""
    db_path = get_db_path(db)

    await manager.connect(websocket, run_id)

    session = None
    try:
        last_event_id = 0

        while True:
            if db_path.exists():
                try:
                    if session is None:
                        session = get_session(db_path)

                    # Clear cached ORM state so queries see fresh DB writes
                    session.expire_all()

                    run_obj = session.get(Run, run_id)
                    run_status = run_obj.status if run_obj else None

                    events_stmt = (
                        select(Event)
                        .where(Event.run_id == run_id)
                        .where(Event.id > last_event_id)  # type: ignore[operator]
                        .order_by(Event.id)
                    )
                    event_results = session.exec(events_stmt).all()
                    events = [e.model_dump() for e in event_results]

                    if events:
                        last_event_id = events[-1]["id"]

                        steps_stmt = (
                            select(Step)
                            .where(Step.run_id == run_id)
                            .order_by(Step.step_index)
                        )
                        step_results = session.exec(steps_stmt).all()
                        steps = [s.model_dump() for s in step_results]

                        await websocket.send_json(
                            {
                                "type": "update",
                                "run_status": run_status,
                                "events": events,
                                "steps": steps,
                            }
                        )

                    if run_status in ("completed", "failed"):
                        await websocket.send_json(
                            {
                                "type": "complete",
                                "status": run_status,
                                "completed_at": run_obj.completed_at,
                            }
                        )
                        break

                except Exception as e:
                    await websocket.send_json({"type": "error", "message": str(e)})
                    # Reset session on error so next iteration creates a fresh one
                    if session:
                        with contextlib.suppress(Exception):
                            session.close()
                        session = None

            await asyncio.sleep(0.1)

    except WebSocketDisconnect:
        pass
    finally:
        if session:
            with contextlib.suppress(Exception):
                session.close()
        manager.disconnect(websocket, run_id)
