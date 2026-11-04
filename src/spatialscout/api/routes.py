"""HTTP API routes under /api."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.sse import EventSourceResponse, ServerSentEvent

from ..agent import Investigation, NoRecordedInvestigation, Orchestrator, RunModeUnavailable, UnknownInvestigation
from ..agent.errors import DatasetUnavailable, InvalidRegions, ReviewRefused, UnknownClaim
from ..audit import verify_chain
from ..contracts import (
    CapabilityReport,
    ChannelSet,
    ChainCheckResult,
    ClaimChallenges,
    ConditionName,
    DatasetManifest,
    LabelRuleSet,
    PackedRegionView,
    InvestigationSnapshot,
    ModeInfo,
    RegionView,
    ReviewRequest,
    RunMode,
    StartInvestigationRequest,
)
from ..data import DatasetStore, SectionNotIngested, SectionTables, UnknownDataset, UnknownLabelRule, UnknownSection
from ..engine import build_packed_region_view, build_region_view, conditions_for, section_channels
from ..gateway import LiveRunRefused, RecordingLibrary
from ..gateway.gate import LiveGate
from ..settings import Settings

router = APIRouter()

# How long a browser EventSource waits before reconnecting after the server ends a stream window.
RECONNECT_DELAY_MS = 500


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
    live_gate: LiveGate = request.app.state.live_gate
    available: list[RunMode] = ["cached_tool_rerun"]
    if recordings.has_recorded_investigations():
        available.insert(0, "immutable_replay")
    if live_gate.enabled:
        available.append("live")
    return ModeInfo(
        dataset_id=settings.dataset_id,
        default_run_mode=settings.default_run_mode,
        available_run_modes=available,
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
    """The whole section as JSON lists, with inclusion flags for every condition the section can compute (the
    exploratory structure-constrained condition only when it has structure masks). For a whole real section prefer
    the packed view."""
    section = _section(store, section_id, label_rule_id)
    conditions = conditions_for(section)
    return build_region_view(section, conditions, synthetic=store.manifest(section.dataset_id).synthetic)


@router.get("/sections/{section_id}/region-view/packed")
def packed_region_view(section_id: str, store: StoreDep, label_rule_id: str | None = None) -> PackedRegionView:
    """The whole section as typed little-endian columns (base64), with one inclusion bit per implemented
    condition. A plain `def`, so packing a large section runs in the thread pool, off the event loop."""
    section = _section(store, section_id, label_rule_id)
    info = store.section_info(section_id)
    conditions = conditions_for(section)
    return build_packed_region_view(
        section, conditions, synthetic=store.manifest(section.dataset_id).synthetic, section_name=info.name, group=info.group
    )


@router.get("/sections/{section_id}/channels")
def channels(section_id: str, store: StoreDep) -> ChannelSet:
    """The section's rendered channels (nuclei and five marker groups), each with its molecule count and whether
    the section has any. The viewer draws them from the packed view's molecules: rendered, not imaged."""
    return section_channels(_section(store, section_id, None))


@router.post("/investigations", status_code=201)
async def start_investigation(
    body: StartInvestigationRequest,
    orchestrator: OrchestratorDep,
    x_live_passcode: Annotated[str | None, Header()] = None,
) -> InvestigationSnapshot:
    """Create a persisted investigation; its plan arrives as an event. A live run needs the passcode in the
    `X-Live-Passcode` header (never the URL, which access logs keep) and budget left today; otherwise 403 and
    nothing is created. Immutable replay returns the recorded investigation that answers the question."""
    try:
        return orchestrator.start(
            body.question, body.run_mode, passcode=x_live_passcode, dataset_id=body.dataset_id, regions=body.regions
        ).snapshot()
    except LiveRunRefused as refused:
        raise HTTPException(status_code=403, detail=str(refused)) from None
    except RunModeUnavailable as unavailable:
        raise HTTPException(status_code=409, detail=str(unavailable)) from None
    except InvalidRegions as invalid:
        raise HTTPException(status_code=422, detail=str(invalid)) from None
    except (NoRecordedInvestigation, DatasetUnavailable) as missing:
        raise HTTPException(status_code=404, detail=str(missing)) from None


@router.get("/investigations/{investigation_id}")
async def get_investigation(investigation: InvestigationDep) -> InvestigationSnapshot:
    return investigation.snapshot()


@router.post("/investigations/{investigation_id}/approve")
async def approve_plan(investigation: InvestigationDep, orchestrator: OrchestratorDep) -> InvestigationSnapshot:
    """Approve the proposed plan. Idempotent: if the investigation is not awaiting approval, this returns its
    current state and starts nothing."""
    return orchestrator.approve(investigation.investigation_id).snapshot()


@router.post("/investigations/{investigation_id}/reject")
async def reject_plan(investigation: InvestigationDep, orchestrator: OrchestratorDep) -> InvestigationSnapshot:
    """Reject the proposed plan: the investigation ends and nothing runs. Idempotent: if the investigation is not
    awaiting approval (already approved, rejected or finished), this returns its current state and changes nothing."""
    return orchestrator.reject(investigation.investigation_id).snapshot()


@router.get("/investigations/{investigation_id}/package")
async def download_package(investigation: InvestigationDep) -> FileResponse:
    path = investigation.directory / "package.zip"
    if not path.is_file():
        raise HTTPException(status_code=409, detail="the evidence package is not ready yet")
    return FileResponse(path, media_type="application/zip", filename=f"spatialscout-{investigation.investigation_id}.zip")


@router.get("/investigations/{investigation_id}/claims/{claim_id}/challenges")
async def claim_challenges(claim_id: str, investigation: InvestigationDep) -> ClaimChallenges:
    """The claim's recorded injected variants and their recorded verifications, for "Challenge the verifier". Read from
    the investigation's files: no model is called and nothing is recomputed."""
    path = investigation.directory / "challenges" / f"{claim_id}.json"
    if "/" in claim_id or not path.is_file():
        raise HTTPException(status_code=404, detail=f"no recorded injected variants for claim {claim_id}")
    return ClaimChallenges.model_validate_json(path.read_text(encoding="utf-8"))


@router.post("/investigations/{investigation_id}/claims/{claim_id}/review")
async def review_claim(claim_id: str, body: ReviewRequest, investigation: InvestigationDep, orchestrator: OrchestratorDep) -> InvestigationSnapshot:
    """Record the researcher's decision on the claim's latest version (reviewer, time and version go in the audit
    log) and export the evidence package again with it. Recorded investigations and unfinished ones are refused."""
    try:
        return orchestrator.review(investigation.investigation_id, claim_id, body).snapshot()
    except UnknownClaim:
        raise HTTPException(status_code=404, detail=f"no claim {claim_id} in {investigation.investigation_id}") from None
    except ReviewRefused as refused:
        raise HTTPException(status_code=409, detail={"code": refused.code, "message": str(refused)}) from None


@router.post("/audit-log/verify")
async def verify_audit_log(request: Request) -> ChainCheckResult:
    """Check the hash chain of an audit log sent as JSONL text, for example the one in an evidence package."""
    return verify_chain((await request.body()).decode("utf-8", errors="replace"))


@router.get("/investigations/{investigation_id}/events", response_class=EventSourceResponse)
async def stream_events(
    request: Request,
    investigation: InvestigationDep,
    after_seq: int = 0,
    last_event_id: Annotated[str | None, Header()] = None,
):
    """Stream every event with `seq > after_seq` over SSE, then new ones until the investigation finishes or the
    stream window closes, whichever comes first. The client then reconnects with `after_seq` (or a browser
    EventSource with the Last-Event-ID header, which counts as `after_seq`) and misses nothing. Each event is sent
    exactly as written to events.jsonl, so an immutable replay is verbatim."""
    settings: Settings = request.app.state.settings
    if last_event_id and last_event_id.isdigit():
        after_seq = max(after_seq, int(last_event_id))
    async for event, line in investigation.events_after(after_seq, settings.stream_window_seconds):
        yield ServerSentEvent(raw_data=line, id=str(event.seq), retry=RECONNECT_DELAY_MS)
