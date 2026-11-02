"""The FastAPI app: the HTTP/SSE API under /api, and the built web app at / (ADR-0004)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles

from ..agent import DEFAULT_REGISTRY, Orchestrator
from ..data import DatasetStore
from ..gateway import RecordingLibrary
from ..settings import Settings
from .routes import router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    orchestrator = Orchestrator(
        store=DatasetStore(settings.fixtures_dir),
        recordings=RecordingLibrary(settings.recordings_dir),
        registry=DEFAULT_REGISTRY,
        investigations_dir=settings.investigations_dir,
        dataset_id=settings.dataset_id,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await orchestrator.shutdown()

    app = FastAPI(title="SpatialScout", lifespan=lifespan)
    app.state.orchestrator = orchestrator
    app.state.settings = settings
    app.include_router(router, prefix="/api")
    if settings.web_dist is not None and (settings.web_dist / "index.html").is_file():
        app.mount("/", StaticFiles(directory=settings.web_dist, html=True), name="web")
    else:

        @app.get("/", include_in_schema=False)
        async def web_not_built() -> PlainTextResponse:
            return PlainTextResponse("The web app is not built yet. Run `make build`, then reload.", status_code=503)

    return app
