"""The investigation orchestrator: a bounded state machine that runs independently of any HTTP connection.

question -> plan proposed -> (approval) -> tool steps -> claim drafted -> package ready

Run modes (ADR-0003): `cached_tool_rerun` serves stored model responses; `live` makes fresh calls once the
live gate admits the passcode, and records them in the investigation's `recording.json`; `immutable_replay`
runs nothing and serves a recorded investigation's events verbatim, read-only, under its original id.
Every model call, live or stored, is written to the audit log and streamed as a `model_call` event.

Work runs in tasks the orchestrator owns, so a client may disconnect and reconnect (with `after_seq`)
without affecting it. Every state change is persisted before it is announced.
"""

import asyncio
import hashlib
import time
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..contracts import (
    AuditResult,
    Claim,
    ClaimDraft,
    ClaimDraftedEvent,
    ErrorEvent,
    FindingRef,
    InvestigationStatus,
    ModelCallEvent,
    ModelCallRecord,
    PackageInfo,
    PackageReadyEvent,
    Plan,
    PlanApprovedEvent,
    PlanProposal,
    PlanProposedEvent,
    Recording,
    ReplayInfo,
    RunMode,
    ToolFinishedEvent,
    ToolStartedEvent,
    checksum,
    new_id,
)
from ..data import DatasetStore
from ..export import AUDIT_LOG_FILE, CLAIMS_FILE, MANIFEST_FILE, build_package
from ..gateway import (
    GatewayError,
    LiveSource,
    ModelGateway,
    RecordingLibrary,
    RecordingWriter,
    ReplaySource,
    ResponseSource,
    StoredResponseMissing,
    normalise_question,
)
from ..gateway.gate import LiveGate
from .errors import InvestigationError, NoRecordedInvestigation, RunModeUnavailable
from .investigation import Investigation
from .prompts import claim_request, plan_request
from .tools import Tool, ToolContext, ToolRegistry


def utc_now() -> datetime:
    return datetime.now(UTC)


class Orchestrator:
    def __init__(
        self,
        *,
        store: DatasetStore,
        recordings: RecordingLibrary,
        registry: ToolRegistry,
        investigations_dir: Path,
        dataset_id: str,
        clock: Callable[[], datetime] = utc_now,
        live_gate: LiveGate | None = None,
    ) -> None:
        self._store = store
        self._recordings = recordings
        self._registry = registry
        self._root = Path(investigations_dir)
        self._dataset_id = dataset_id
        self._clock = clock
        self._live_gate = live_gate
        self._investigations: dict[str, Investigation] = {}
        self._gateways: dict[str, ModelGateway] = {}
        self._tasks: set[asyncio.Task[None]] = set()

    def start(self, question: str, run_mode: RunMode, passcode: str | None = None) -> Investigation:
        """Create and persist an investigation, then propose its plan in the background.

        `immutable_replay` instead returns the recorded investigation that answers the question (or raises
        NoRecordedInvestigation). `live` first asks the live gate, which raises LiveRunRefused before anything
        is created when the passcode is wrong, live runs are not configured or today's budget is spent.
        """
        question = normalise_question(question)
        if run_mode == "immutable_replay":
            return self._replay(question)
        if run_mode == "live":
            if self._live_gate is None:
                raise RunModeUnavailable("Live runs are not enabled on this server.")
            self._live_gate.admit(passcode)
        # Only a cached tool rerun plays a recording's stored responses; a live run makes its own and is labelled live.
        recording = self._recordings.for_question(question) if run_mode == "cached_tool_rerun" else None
        investigation = Investigation.create(
            self._root, question, run_mode, self._dataset_id, recording.info if recording else None, self._clock
        )
        investigation.audit_log.append(
            "investigation_started",
            {"question": question, "run_mode": run_mode, "dataset_id": self._dataset_id,
             "recording_id": recording.info.recording_id if recording else None},
        )
        self._investigations[investigation.investigation_id] = investigation
        self._spawn(investigation, self._propose_plan(investigation, recording))
        return investigation

    def get(self, investigation_id: str) -> Investigation:
        """An investigation by id, from memory or, after a restart, from its directory.

        One loaded from disk while planning or running lost its task when the server stopped, so it is failed
        as interrupted rather than left for clients to wait on. One awaiting approval can still be approved.
        """
        if investigation_id not in self._investigations:
            recorded = self._recordings.recorded_investigation_by_id(investigation_id)
            if recorded is not None:
                directory, info = recorded
                self._investigations[investigation_id] = Investigation.load_recorded(directory, info, self._clock)
                return self._investigations[investigation_id]
            investigation = Investigation.load(self._root, investigation_id, self._clock)
            self._investigations[investigation_id] = investigation
            if investigation.state.status in (InvestigationStatus.PLANNING, InvestigationStatus.RUNNING):
                self._fail(investigation, "interrupted", "The server stopped before this investigation finished; ask again.")
        return self._investigations[investigation_id]

    def approve(self, investigation_id: str) -> Investigation:
        """Freeze the proposed plan and start executing it.

        Idempotent: unless the investigation is awaiting approval, this returns it unchanged and starts nothing.
        The status check and the move to `running` happen with no await between them, so two approvals that
        arrive together cannot both start the plan.
        """
        investigation = self.get(investigation_id)
        plan = investigation.plan()
        if investigation.read_only or investigation.state.status != InvestigationStatus.AWAITING_APPROVAL or plan is None:
            return investigation
        plan_hash = checksum(plan)
        investigation.update_state(status=InvestigationStatus.RUNNING, approved_plan_hash=plan_hash, approved_at_utc=self._clock())
        investigation.audit_log.append("plan_approved", {"plan_id": plan.plan_id, "plan_hash": plan_hash})
        investigation.emit(PlanApprovedEvent, plan_id=plan.plan_id, plan_hash=plan_hash)
        self._spawn(investigation, self._execute(investigation, investigation.plan()))
        return investigation

    async def shutdown(self) -> None:
        for task in list(self._tasks):
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        if self._live_gate is not None:
            await self._live_gate.aclose()

    def _replay(self, question: str) -> Investigation:
        recorded = self._recordings.recorded_investigation(question)
        if recorded is None:
            raise NoRecordedInvestigation(f"No recorded investigation answers {question!r}; ask one of the recorded questions.")
        directory, info = recorded
        investigation = Investigation.load_recorded(directory, info, self._clock)
        return self._investigations.setdefault(investigation.investigation_id, investigation)

    def _spawn(self, investigation: Investigation, work: Coroutine[Any, Any, None]) -> None:
        task = asyncio.get_running_loop().create_task(self._guarded(investigation, work))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _guarded(self, investigation: Investigation, work: Coroutine[Any, Any, None]) -> None:
        """Run a step of the investigation; any failure becomes an error event and a failed status."""
        try:
            await work
        except asyncio.CancelledError:
            raise
        except (InvestigationError, GatewayError) as error:
            self._fail(investigation, error.code, str(error))
        except Exception as error:  # noqa: BLE001 - an unexpected failure must still end the stream
            self._fail(investigation, "internal_error", f"{type(error).__name__}: {error}")

    def _fail(self, investigation: Investigation, code: str, message: str) -> None:
        investigation.audit_log.append("error", {"code": code, "message": message})
        investigation.emit(ErrorEvent, status=InvestigationStatus.FAILED, code=code, message=message)

    def _gateway(self, investigation: Investigation, recording: Recording | None) -> ModelGateway:
        """The investigation's gateway: stored responses for a cached tool rerun, fresh recorded calls for a live run."""
        gateway = self._gateways.get(investigation.investigation_id)
        if gateway is not None:
            return gateway
        state = investigation.state
        source: ResponseSource
        recorder = None
        if state.run_mode == "live":
            if self._live_gate is None or not self._live_gate.enabled:
                raise RunModeUnavailable("Live runs are not enabled on this server.")
            source = LiveSource(self._live_gate.client, recording_id=investigation.investigation_id)
            recorder = RecordingWriter(
                investigation.directory / "recording.json",
                ReplayInfo(
                    recording_id=investigation.investigation_id,
                    recorded_at=state.created_at_utc,
                    origin="live",
                    question=state.question,
                    note="Model responses recorded from a live run.",
                ),
            )
        elif state.run_mode == "cached_tool_rerun":
            if recording is None:
                raise StoredResponseMissing(
                    "No stored model responses answer this question. A cached tool rerun can only ask recorded questions."
                )
            source = ReplaySource(recording)
        else:
            raise RunModeUnavailable(f"{state.run_mode} never calls a model")
        gateway = ModelGateway(
            source,
            self._clock,
            run_mode=state.run_mode,
            on_call=lambda record: self._model_call(investigation, record),
            recorder=recorder,
        )
        self._gateways[investigation.investigation_id] = gateway
        return gateway

    def _model_call(self, investigation: Investigation, record: ModelCallRecord) -> None:
        """Audit and stream one model call: provider, model, purpose, latency, tokens, cost, live or stored."""
        investigation.audit_log.append("model_call", record.model_dump(mode="json"))
        investigation.emit(ModelCallEvent, call=record)

    async def _propose_plan(self, investigation: Investigation, recording: Recording | None) -> None:
        gateway = self._gateway(investigation, recording)
        state = investigation.state
        request, inputs = plan_request(state.question, self._store.capability_report(state.dataset_id), self._registry.specs())
        proposal, _ = await gateway.complete_json("plan", request, inputs, PlanProposal)
        plan = self._registry.plan_from(
            proposal,
            investigation_id=investigation.investigation_id,
            question=state.question,
            dataset_id=state.dataset_id,
            proposed_by=request.model,
        )
        investigation.audit_log.append("plan_proposed", {"plan": plan.model_dump(mode="json")})
        investigation.emit(PlanProposedEvent, status=InvestigationStatus.AWAITING_APPROVAL, plan=plan)

    async def _execute(self, investigation: Investigation, plan: Plan) -> None:
        """Run the frozen plan's tool steps, draft one claim per finding, then export the package."""
        context = ToolContext(store=self._store)
        findings: list[tuple[Tool, AuditResult]] = []
        for step in plan.steps:
            tool = self._registry.get(step.tool)
            arguments = tool.arguments.model_validate(step.arguments)
            investigation.emit(ToolStartedEvent, step_id=step.step_id, tool=tool.name, arguments=step.arguments)
            started = time.perf_counter()
            artifact = await asyncio.to_thread(tool.run, arguments, context)
            artifact_id = _artifact_id(artifact)
            artifacts_dir = investigation.directory / "artifacts"
            artifacts_dir.mkdir(exist_ok=True)
            (artifacts_dir / f"{artifact_id}.json").write_text(artifact.model_dump_json(indent=1), encoding="utf-8")
            investigation.audit_log.append(
                "tool_call",
                {"step_id": step.step_id, "tool": tool.name, "tool_version": tool.version, "arguments": step.arguments,
                 "artifact_id": artifact_id, "artifact_sha256": checksum(artifact),
                 "duration_ms": round((time.perf_counter() - started) * 1000)},
            )
            investigation.emit(ToolFinishedEvent, step_id=step.step_id, tool=tool.name, artifact_id=artifact_id, summary=tool.summarize(artifact))
            if isinstance(artifact, AuditResult):
                findings.append((tool, artifact))
        claims = []
        for tool, finding in findings:
            claim = await self._draft_claim(investigation, tool, finding)
            investigation.audit_log.append("claim_drafted", {"claim": claim.model_dump(mode="json")})
            investigation.emit(ClaimDraftedEvent, claim=claim)
            claims.append(claim)
        package = self._export(investigation, claims)
        investigation.emit(PackageReadyEvent, status=InvestigationStatus.COMPLETE, package=package)

    async def _draft_claim(self, investigation: Investigation, tool: Tool, finding: AuditResult) -> Claim:
        """Draft a claim from stored model responses. Its evidence status is the finding's computed label,
        never the model's; verification and review start pending and unreviewed."""
        gateway = self._gateway(investigation, self._recordings.for_question(investigation.state.question))
        request, inputs = claim_request(investigation.state.question, finding, tool.spec())
        draft, _ = await gateway.complete_json("claim_draft", request, inputs, ClaimDraft)
        return Claim(
            claim_id=new_id("clm"),
            investigation_id=investigation.investigation_id,
            dataset_id=finding.dataset_id,
            finding=FindingRef(finding_id=finding.finding_id, finding_kind=finding.finding_kind),
            text=draft.text,
            cited=draft.cited,
            evidence_status=finding.label,
        )

    def _export(self, investigation: Investigation, claims: list[Claim]) -> PackageInfo:
        """Write the evidence package, then log the export. The package's manifest anchors the audit log at
        its head hash; the export entry that follows it stays in the server's log."""
        state = investigation.state
        manifest = build_package(
            investigation.directory / "package.zip",
            investigation_id=investigation.investigation_id,
            question=state.question,
            run_mode=state.run_mode,
            replay=state.replay,
            dataset=self._store.manifest(state.dataset_id),
            plan=investigation.plan(),
            claims=claims,
            audit_log_text=investigation.audit_log.text(),
            created_at=self._clock(),
        )
        investigation.audit_log.append(
            "package_exported",
            {"package_id": manifest.package_id, "audit_log_head_hash": manifest.audit_log.head_hash,
             "package_sha256": hashlib.sha256((investigation.directory / "package.zip").read_bytes()).hexdigest()},
        )
        return PackageInfo(
            package_id=manifest.package_id,
            download_url=f"/api/investigations/{investigation.investigation_id}/package",
            created_at=manifest.created_at,
            files=[CLAIMS_FILE, AUDIT_LOG_FILE, MANIFEST_FILE],
            audit_log=manifest.audit_log,
            review_state=manifest.review_state,
        )


def _artifact_id(artifact: Any) -> str:
    for field in ("control_id", "finding_id", "artifact_id"):
        if isinstance(getattr(artifact, field, None), str):
            return getattr(artifact, field)
    raise TypeError(f"a tool returned an artifact without an id: {type(artifact).__name__}")
