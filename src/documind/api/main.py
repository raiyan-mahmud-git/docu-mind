"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI

from documind.api.routes import router
from documind.config import Settings
from documind.runtime import Runtime, create_runtime


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Create one runtime per process and close its persistent store on shutdown."""
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
    return app


app = create_app()

