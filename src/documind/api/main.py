"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from documind.api.routes import router
from documind.config import Settings
from documind.logging_config import configure_logging
from documind.runtime import Runtime, create_runtime


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Create one runtime per process and close its persistent store on shutdown."""
    configure_logging()
    factory: Callable[[], Runtime] = app.state.runtime_factory
    app.state.runtime = factory()
    try:
        yield
    finally:
        app.state.runtime.close()


def create_app(
    settings: Settings | None = None,
    runtime_factory: Callable[[], Runtime] | None = None,
) -> FastAPI:
    """Create the API, optionally using isolated settings and services for tests."""
    active_settings = settings or Settings.from_env()

    def default_factory() -> Runtime:
        return create_runtime(active_settings)

    app = FastAPI(
        title="DocuMind API",
        description="Local document ingestion and cited semantic search.",
        version="0.1.0",
        lifespan=_lifespan,
    )
    app.state.settings = active_settings
    app.state.runtime_factory = runtime_factory or default_factory
    app.include_router(router)

    web_dir = Path(__file__).resolve().parents[3] / "web"
    if web_dir.is_dir():
        app.mount("/static", StaticFiles(directory=web_dir), name="static")
        app.add_api_route(
            "/",
            lambda: FileResponse(web_dir / "index.html"),
            methods=["GET"],
            include_in_schema=False,
        )
    return app


app = create_app()
