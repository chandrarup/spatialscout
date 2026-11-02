"""HTTP API routes under /api."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.sse import EventSourceResponse, ServerSentEvent

from ..agent import Investigation, Orchestrator, UnknownInvestigation
from ..audit import verify_chain
from ..contracts import ChainCheckResult, InvestigationSnapshot, StartInvestigationRequest

router = APIRouter()


def _orchestrator(request: Request) -> Orchestrator:
    return request.app.state.orchestrator


def _investigation(investigation_id: str, orchestrator: Annotated[Orchestrator, Depends(_orchestrator)]) -> Investigation:
    try:
        return orchestrator.get(investigation_id)
    except UnknownInvestigation:
        raise HTTPException(status_code=404, detail=f"no investigation {investigation_id}") from None


OrchestratorDep = Annotated[Orchestrator, Depends(_orchestrator)]
InvestigationDep = Annotated[Investigation, Depends(_investigation)]


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/investigations", status_code=201)
async def start_investigation(body: StartInvestigationRequest, orchestrator: OrchestratorDep) -> InvestigationSnapshot:
    """Create a persisted investigation; its plan arrives as an event."""
    return orchestrator.start(body.question, body.run_mode).snapshot()


@router.get("/investigations/{investigation_id}")
async def get_investigation(investigation: InvestigationDep) -> InvestigationSnapshot:
    return investigation.snapshot()


@router.post("/investigations/{investigation_id}/approve")
async def approve_plan(investigation: InvestigationDep, orchestrator: OrchestratorDep) -> InvestigationSnapshot:
    """Approve the proposed plan. Idempotent: if the investigation is not awaiting approval, this returns its
    current state and starts nothing."""
    return orchestrator.approve(investigation.investigation_id).snapshot()


@router.get("/investigations/{investigation_id}/package")
async def download_package(investigation: InvestigationDep) -> FileResponse:
    path = investigation.directory / "package.zip"
    if not path.is_file():
        raise HTTPException(status_code=409, detail="the evidence package is not ready yet")
    return FileResponse(path, media_type="application/zip", filename=f"spatialscout-{investigation.investigation_id}.zip")


@router.post("/audit-log/verify")
async def verify_audit_log(request: Request) -> ChainCheckResult:
    """Check the hash chain of an audit log sent as JSONL text, for example the one in an evidence package."""
    return verify_chain((await request.body()).decode("utf-8", errors="replace"))


@router.get("/investigations/{investigation_id}/events", response_class=EventSourceResponse)
async def stream_events(
    investigation: InvestigationDep,
    after_seq: int = 0,
    last_event_id: Annotated[str | None, Header()] = None,
):
    """Stream every event with `seq > after_seq` over SSE, then new ones until the investigation finishes.
    A browser EventSource reconnects with the Last-Event-ID header, which counts as `after_seq`."""
    if last_event_id and last_event_id.isdigit():
        after_seq = max(after_seq, int(last_event_id))
    async for event in investigation.events_after(after_seq):
        yield ServerSentEvent(raw_data=event.model_dump_json(), id=str(event.seq))
