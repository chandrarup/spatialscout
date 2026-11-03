"""HTTP API routes under /api."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.sse import EventSourceResponse, ServerSentEvent

from ..agent import Investigation, Orchestrator, UnknownInvestigation
from ..audit import verify_chain
from ..contracts import (
    CapabilityReport,
    ChainCheckResult,
    ConditionName,
    DatasetManifest,
    LabelRuleSet,
    PackedRegionView,
    InvestigationSnapshot,
    ModeInfo,
    RegionView,
    StartInvestigationRequest,
)
from ..data import DatasetStore, SectionNotIngested, SectionTables, UnknownDataset, UnknownLabelRule, UnknownSection
from ..engine import IMPLEMENTED_CONDITIONS, build_packed_region_view, build_region_view
from ..gateway import RecordingLibrary
from ..settings import Settings

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


def _store(request: Request) -> DatasetStore:
    return request.app.state.store


StoreDep = Annotated[DatasetStore, Depends(_store)]


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/mode")
async def mode(request: Request) -> ModeInfo:
    """How questions are answered now, and the recordings a cached tool rerun can play."""
    settings: Settings = request.app.state.settings
    recordings: RecordingLibrary = request.app.state.recordings
    return ModeInfo(
        dataset_id=settings.dataset_id,
        default_run_mode=settings.default_run_mode,
        available_run_modes=["cached_tool_rerun"],
        recordings=recordings.infos(),
    )


@router.get("/datasets")
async def datasets(store: StoreDep) -> list[DatasetManifest]:
    """Every dataset the store serves, by manifest."""
    return [store.manifest(dataset_id) for dataset_id in store.dataset_ids()]


@router.get("/datasets/{dataset_id}")
async def dataset_manifest(dataset_id: str, store: StoreDep) -> DatasetManifest:
    try:
        return store.manifest(dataset_id)
    except UnknownDataset:
        raise HTTPException(status_code=404, detail=f"no dataset {dataset_id}") from None


@router.get("/datasets/{dataset_id}/capability-report")
async def capability_report(dataset_id: str, store: StoreDep) -> CapabilityReport:
    """What the dataset supports, what is unavailable and why, and every contrast's inference eligibility."""
    try:
        return store.capability_report(dataset_id)
    except UnknownDataset:
        raise HTTPException(status_code=404, detail=f"no dataset {dataset_id}") from None


@router.get("/datasets/{dataset_id}/label-rules")
async def label_rules(dataset_id: str, store: StoreDep) -> LabelRuleSet:
    """The frozen label rules, their gene scales and per-section counts under each rule."""
    try:
        rules = store.label_rules(dataset_id)
    except UnknownDataset:
        raise HTTPException(status_code=404, detail=f"no dataset {dataset_id}") from None
    if rules is None:
        raise HTTPException(status_code=404, detail=f"dataset {dataset_id} labels its cells by construction, with no label rule")
    return rules


def _section(store: DatasetStore, section_id: str, label_rule_id: str | None) -> SectionTables:
    try:
        return store.load_section(section_id, label_rule_id)
    except UnknownSection:
        raise HTTPException(status_code=404, detail=f"no section {section_id}") from None
    except UnknownLabelRule:
        raise HTTPException(status_code=404, detail=f"no label rule {label_rule_id} for section {section_id}") from None
    except SectionNotIngested as error:
        raise HTTPException(status_code=409, detail=str(error)) from None


@router.get("/sections/{section_id}/region-view")
async def region_view(section_id: str, store: StoreDep, label_rule_id: str | None = None) -> RegionView:
    """The whole section as JSON lists, with inclusion flags for every implemented condition. For a whole real
    section prefer the packed view."""
    section = _section(store, section_id, label_rule_id)
    conditions = [c for c in ConditionName if c in IMPLEMENTED_CONDITIONS]
    return build_region_view(section, conditions, synthetic=store.manifest(section.dataset_id).synthetic)


@router.get("/sections/{section_id}/region-view/packed")
def packed_region_view(section_id: str, store: StoreDep, label_rule_id: str | None = None) -> PackedRegionView:
    """The whole section as typed little-endian columns (base64), with one inclusion bit per implemented
    condition. A plain `def`, so packing a large section runs in the thread pool, off the event loop."""
    section = _section(store, section_id, label_rule_id)
    info = store.section_info(section_id)
    conditions = [c for c in ConditionName if c in IMPLEMENTED_CONDITIONS]
    return build_packed_region_view(
        section, conditions, synthetic=store.manifest(section.dataset_id).synthetic, section_name=info.name, group=info.group
    )


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
