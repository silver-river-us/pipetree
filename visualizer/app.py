"""Pipetree Visualizer - Real-time monitoring dashboard."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from infra.db import init_db, run_migrations
from boundary.base.http_context import get_current_user
from routes import register_routes


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        request.state.user = get_current_user(request)
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[arg-type]
    init_db()
    run_migrations()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Pipetree Visualizer", version="1.0.0", lifespan=lifespan)
    app.add_middleware(AuthMiddleware)
    register_routes(app)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
