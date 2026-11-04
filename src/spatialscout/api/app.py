"""The FastAPI app: the HTTP/SSE API under /api, and the built web app at / (ADR-0004)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx2 as httpx
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles

from ..agent import DEFAULT_REGISTRY, Orchestrator
from ..data import DatasetStore
from ..agent import utc_now
from ..gateway import LIST_PRICES, ApiKeys, PriceBook, RecordingLibrary
from ..gateway.gate import LiveGate
from ..settings import Settings
from .audit_routes import router as audit_router
from .routes import router
from .structure_routes import router as structure_router
from .voice import router as voice_router


def create_app(
    settings: Settings | None = None,
    *,
    model_transport: httpx.AsyncBaseTransport | None = None,
    prices: PriceBook = LIST_PRICES,
    api_keys: ApiKeys | None = None,
) -> FastAPI:
    """The app. Tests pass `model_transport` (recorded provider responses), fake `prices` and fake `api_keys`;
    deployed, keys come from the environment (or `SPATIALSCOUT_ENV_FILE`) and never leave the backend."""
    settings = settings or Settings.from_env()
    store = DatasetStore(settings.fixtures_dir, artifacts_dir=settings.artifacts_dir, processed_dir=settings.processed_dir)
    recordings = RecordingLibrary(settings.recordings_dir)
    live = settings.live
    live_gate = LiveGate(
        passcode=live.passcode,
        daily_budget_usd=live.daily_budget_usd,
        spend_dir=live.spend_dir,
        keys=api_keys or ApiKeys.from_env(live.env_file),
        clock=utc_now,
        prices=prices,
        transport=model_transport,
    )
    orchestrator = Orchestrator(
        store=store,
        recordings=recordings,
        registry=DEFAULT_REGISTRY,
        investigations_dir=settings.investigations_dir,
        dataset_id=settings.dataset_id,
        live_gate=live_gate,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await orchestrator.shutdown()

    app = FastAPI(title="SpatialScout", lifespan=lifespan)
    # A packed whole-section region view is several MB; gzip halves it. SSE streams are never compressed.
    app.add_middleware(GZipMiddleware, minimum_size=4096)
    app.state.orchestrator = orchestrator
    app.state.store = store
    app.state.recordings = recordings
    app.state.settings = settings
    app.state.live_gate = live_gate
    app.include_router(router, prefix="/api")
    app.include_router(audit_router, prefix="/api")
    app.include_router(voice_router, prefix="/api")
    app.include_router(structure_router, prefix="/api")
    if settings.web_dist is not None and (settings.web_dist / "index.html").is_file():
        app.mount("/", StaticFiles(directory=settings.web_dist, html=True), name="web")
    else:

        @app.get("/", include_in_schema=False)
        async def web_not_built() -> PlainTextResponse:
            return PlainTextResponse("The web app is not built yet. Run `make build`, then reload.", status_code=503)

    return app
