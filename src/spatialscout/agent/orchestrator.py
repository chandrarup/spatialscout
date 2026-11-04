"""The investigation orchestrator: a bounded state machine that runs independently of any HTTP connection.

question -> plan proposed (Muse Wonder; checked, one re-plan) -> approval (or rejection) -> plan steps ->
agent follow-ups (Muse Spark 1.3, within the tool-call budget) -> claims drafted in parallel (Muse Spark Open) ->
claims verified (structural, independent numerical recompute, visual check by Muse Spark 1.3), with their injected
variants recorded for "Challenge the verifier" -> package ready

The agent loop: after the plan's steps run, Muse Spark 1.3 reads each observation in turn and may request follow-up
tools, each citing the observation that prompted it. Every request is validated (a registered tool, arguments valid
for the dataset, a real observation, not a repeat) before it runs, and each follow-up's result is itself an
observation the agent reads next. The orchestrator runs only what the agent requests: it never runs a control on its
behalf, so a claim whose required control the agent skipped carries no control and fails verification (ticket 10).
The plan's budget counts every tool call, plan steps included; when it is spent, the agent's unrun requests and its
unread observations become open questions, and the investigation drafts claims from the evidence it has.

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
from collections.abc import Callable, Coroutine, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..contracts import (
    AgentDecisionEvent,
    AuditResult,
    BudgetExhaustedEvent,
    CapabilityReport,
    Claim,
    ClaimControls,
    ClaimDraft,
    ClaimDraftedEvent,
    ClaimRejectedEvent,
    ClaimVerifiedEvent,
    DatasetManifest,
    InjectedErrorKind,
    ErrorEvent,
    FindingRef,
    FollowUpDecision,
    FollowUpProposal,
    FollowUpRequest,
    FollowUpStatus,
    InvestigationStatus,
    LabelSensitivityCheck,
    ModelCallEvent,
    ModelCallRecord,
    OpenQuestion,
    PackageInfo,
    PackageReadyEvent,
    Plan,
    PlanApprovedEvent,
    PlanProposal,
    PlanProposedEvent,
    PlanRejectedEvent,
    RandomThinningControl,
    Recording,
    Region,
    ReplayInfo,
    RunMode,
    ToolFailedEvent,
    ToolFinishedEvent,
    ToolStartedEvent,
    canonical_json,
    checksum,
    new_id,
)
from ..data import DatasetStore
from ..engine.figure import render_composite_figure
from ..verify.verifier import VerificationContext, challenge, reasons_of, verify_claim
from ..export import AUDIT_LOG_FILE, CLAIMS_FILE, MANIFEST_FILE, build_package
from ..gateway import (
    GatewayError,
    LiveSource,
    ModelGateway,
    ModelOutputInvalid,
    ModelOutputTruncated,
    RecordingLibrary,
    RecordingWriter,
    ReplaySource,
    ResponseSource,
    StoredResponseMissing,
    normalise_question,
)
from ..gateway.gate import LiveGate
from .claims import claim_problems
from .errors import (
    DatasetUnavailable,
    InvalidRegions,
    InvestigationError,
    NoRecordedInvestigation,
    PlanInvalid,
    PlanUnsupported,
    RunModeUnavailable,
    ToolCallInvalid,
)
from .investigation import Investigation
from .prompts import (
    claim_request,
    dataset_context,
    follow_up_request,
    observation_view,
    plan_request,
    redraft_request,
    replan_request,
)
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

    def start(
        self,
        question: str,
        run_mode: RunMode,
        passcode: str | None = None,
        dataset_id: str | None = None,
        regions: Sequence[Region] = (),
    ) -> Investigation:
        """Create and persist an investigation, then propose its plan in the background.

        `immutable_replay` instead returns the recorded investigation that answers the question (or raises
        NoRecordedInvestigation). `live` first asks the live gate, which raises LiveRunRefused before anything
        is created when the passcode is wrong, live runs are not configured or today's budget is spent.
        The dataset is the recording's for a cached tool rerun, else the one asked for, else the server's default.
        `regions` (drawn in the viewer) are kept as context and must lie on that dataset's sections, else
        InvalidRegions; immutable replay ignores them.
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
        dataset_id = (recording.info.dataset_id if recording else None) or dataset_id or self._dataset_id
        if dataset_id not in self._store.dataset_ids():
            raise DatasetUnavailable(f"No dataset {dataset_id!r} is served here.")
        sections = {s.section_id for s in self._store.sections(dataset_id)}
        stray = [r.section_id for r in regions if r.section_id not in sections]
        if stray:
            raise InvalidRegions(f"Regions on {', '.join(stray)} are not on a section of {dataset_id}.")
        investigation = Investigation.create(
            self._root, question, run_mode, dataset_id, recording.info if recording else None, self._clock, regions
        )
        started = {"question": question, "run_mode": run_mode, "dataset_id": dataset_id,
                   "recording_id": recording.info.recording_id if recording else None}
        if regions:  # only when drawn, so investigations without regions log exactly what they did before
            started["regions"] = [r.model_dump(mode="json") for r in regions]
        investigation.audit_log.append("investigation_started", started)
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

    def reject(self, investigation_id: str) -> Investigation:
        """The researcher rejects the proposed plan: the investigation ends and nothing runs. Idempotent like approval;
        a plan already approved can no longer be rejected."""
        investigation = self.get(investigation_id)
        plan = investigation.plan()
        if investigation.read_only or investigation.state.status != InvestigationStatus.AWAITING_APPROVAL or plan is None:
            return investigation
        reason = "The researcher rejected the plan; nothing ran."
        investigation.audit_log.append("plan_rejected", {"by": "researcher", "plan_id": plan.plan_id, "reason": reason})
        investigation.emit(
            PlanRejectedEvent,
            status=InvestigationStatus.REJECTED,
            by="researcher",
            attempt=1,
            reason=reason,
            tools=[step.tool for step in plan.steps],
            plan_id=plan.plan_id,
        )
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

    def _recording(self, investigation: Investigation) -> Recording | None:
        if investigation.state.run_mode != "cached_tool_rerun":
            return None
        return self._recordings.for_question(investigation.state.question)

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
                    dataset_id=state.dataset_id,
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

    # --- plan ----------------------------------------------------------------------------------------------

    async def _propose_plan(self, investigation: Investigation, recording: Recording | None) -> None:
        """Muse Wonder proposes a plan, checked against the registry, the capability report and the dataset. A rejected
        proposal gets one re-plan with the reason; a second rejection ends the investigation with the limitation."""
        gateway = self._gateway(investigation, recording)
        state = investigation.state
        report, manifest = self._store.capability_report(state.dataset_id), self._store.manifest(state.dataset_id)
        context = dataset_context(manifest, self._store.label_rules(state.dataset_id))
        plannable = self._registry.specs(plannable_only=True)
        request, inputs = plan_request(state.question, report, plannable, context)
        for attempt in (1, 2):
            proposal, _ = await gateway.complete_json("plan" if attempt == 1 else "replan", request, inputs, PlanProposal)
            try:
                plan = self._registry.plan_from(
                    proposal,
                    investigation_id=investigation.investigation_id,
                    question=state.question,
                    dataset_id=state.dataset_id,
                    proposed_by=request.model,
                    report=report,
                    dataset=manifest,
                )
            except PlanInvalid as rejected:
                tools = [step.tool for step in proposal.steps]
                investigation.audit_log.append(
                    "plan_rejected", {"by": "validator", "attempt": attempt, "reason": str(rejected), "tools": tools}
                )
                investigation.emit(PlanRejectedEvent, by="validator", attempt=attempt, reason=str(rejected), tools=tools)
                if attempt == 2:
                    supported = ", ".join(c.capability for c in report.checks if c.status != "unavailable")
                    raise PlanUnsupported(
                        f"SpatialScout cannot plan this question on {state.dataset_id}: the re-plan was rejected too "
                        f"({rejected}). A plan can use {', '.join(t.name for t in plannable)}, and the dataset supports "
                        f"{supported}."
                    ) from rejected
                request = replan_request(request, proposal.model_dump_json(), str(rejected))
                continue
            investigation.audit_log.append("plan_proposed", {"plan": plan.model_dump(mode="json")})
            investigation.emit(PlanProposedEvent, status=InvestigationStatus.AWAITING_APPROVAL, plan=plan)
            return

    # --- execution and the agent loop ------------------------------------------------------------------------

    async def _execute(self, investigation: Investigation, plan: Plan) -> None:
        """Run the frozen plan's steps, let the agent read every observation and request follow-ups within the budget,
        draft one claim per audit result of the plan in parallel, then export the package."""
        frozen = plan.model_copy(update={"status": "proposed", "plan_hash": None, "approved_at_utc": None})
        if checksum(frozen) != investigation.state.approved_plan_hash:
            raise PlanInvalid("the plan about to run is not the plan that was approved")
        run = _Run(plan=plan)
        report, manifest = self._store.capability_report(investigation.state.dataset_id), self._store.manifest(investigation.state.dataset_id)
        for step in plan.steps:
            tool, arguments = self._registry.validate_call(step.tool, step.arguments, report, manifest)
            await self._run_tool(investigation, run, tool, arguments, step.arguments, step_id=step.step_id, reason=step.rationale)
        await self._follow_up(investigation, run, report, manifest)
        claims = await self._draft_claims(investigation, run)
        claims = await self._verify_claims(investigation, run, claims)
        package = self._export(investigation, claims, run.open_questions)
        investigation.emit(PackageReadyEvent, status=InvestigationStatus.COMPLETE, package=package)

    async def _run_tool(
        self,
        investigation: Investigation,
        run: "_Run",
        tool: Tool,
        arguments: Any,
        raw_arguments: dict[str, Any],
        *,
        step_id: str,
        reason: str,
        request_id: str | None = None,
        cites: str | None = None,
    ) -> "_Observation":
        """Run one validated tool call and record its observation. A tool that raises yields a failed observation,
        which the agent reads like any other."""
        observation = _Observation(f"obs-{len(run.observations) + 1}", step_id, tool, raw_arguments, request_id, cites, reason)
        run.observations.append(observation)
        investigation.emit(
            ToolStartedEvent,
            step_id=step_id,
            tool=tool.name,
            arguments=raw_arguments,
            observation_id=observation.observation_id,
            request_id=request_id,
            cites_observation_id=cites,
            reason=reason,
        )
        started = time.perf_counter()
        call = {"step_id": step_id, "tool": tool.name, "tool_version": tool.version, "arguments": raw_arguments,
                "observation_id": observation.observation_id, "request_id": request_id, "cites_observation_id": cites}
        try:
            artifact = await asyncio.to_thread(tool.run, arguments, ToolContext(store=self._store))
        except Exception as error:  # noqa: BLE001 - a failed tool call is an observation, not the end of the run
            observation.error = f"{type(error).__name__}: {error}"
            investigation.audit_log.append("tool_failed", {**call, "error": observation.error})
            investigation.emit(ToolFailedEvent, step_id=step_id, tool=tool.name, observation_id=observation.observation_id, error=observation.error)
            return observation
        observation.artifact = artifact
        artifact_id = _artifact_id(artifact)
        artifacts_dir = investigation.directory / "artifacts"
        artifacts_dir.mkdir(exist_ok=True)
        (artifacts_dir / f"{artifact_id}.json").write_text(artifact.model_dump_json(indent=1), encoding="utf-8")
        investigation.audit_log.append(
            "tool_call",
            {**call, "artifact_id": artifact_id, "artifact_sha256": checksum(artifact),
             "duration_ms": round((time.perf_counter() - started) * 1000)},
        )
        observation.summary = tool.summarize(artifact)
        investigation.emit(
            ToolFinishedEvent,
            step_id=step_id,
            tool=tool.name,
            artifact_id=artifact_id,
            summary=observation.summary,
            observation_id=observation.observation_id,
            label=getattr(artifact, "label", None),
        )
        return observation

    async def _follow_up(self, investigation: Investigation, run: "_Run", report: CapabilityReport, manifest: DatasetManifest) -> None:
        """Muse Spark 1.3 reads each observation in turn and may request follow-up tools, each citing an observation.
        Only what it requests runs. When the budget is spent, what is left becomes open questions."""
        gateway = self._gateway(investigation, self._recording(investigation))
        budget = run.plan.budget.max_tool_calls
        tools = self._registry.specs()
        unread = [o.observation_id for o in run.observations]
        over_budget = False
        while unread and run.tool_calls < budget:
            inspected = unread.pop(0)
            request, inputs = follow_up_request(
                investigation.state.question, run.plan, [o.view() for o in run.observations], inspected, tools, run.tool_calls
            )
            decision, _ = await gateway.complete_json("follow_up", request, inputs, FollowUpDecision)
            records: list[FollowUpRequest] = []
            for proposal in decision.requests:
                run.requests += 1
                request_id = f"req-{run.requests}"
                problem = self._follow_up_problem(run, proposal, records, report, manifest)
                status: FollowUpStatus = "rejected" if problem else "accepted"
                accepted_so_far = sum(r.status == "accepted" for r in records)
                if problem is None and run.tool_calls + accepted_so_far >= budget:
                    status, problem, over_budget = "over_budget", f"the {budget}-call budget is spent", True
                    run.open_questions.append(
                        OpenQuestion(
                            text=f"Not run because the budget was spent: {proposal.tool}, requested on {proposal.cites_observation}. "
                            f"{proposal.reason}",
                            source="over_budget_request",
                            observation_id=proposal.cites_observation,
                            request_id=request_id,
                        )
                    )
                records.append(
                    FollowUpRequest(
                        request_id=request_id,
                        tool=proposal.tool,
                        arguments=proposal.arguments,
                        cites_observation_id=proposal.cites_observation,
                        reason=proposal.reason,
                        status=status,
                        rejection_reason=problem,
                    )
                )
            run.open_questions += [OpenQuestion(text=q, source="agent", observation_id=inspected) for q in decision.open_questions]
            investigation.audit_log.append(
                "agent_decision",
                {"observation_id": inspected, "reading": decision.reading, "requests": [r.model_dump(mode="json") for r in records],
                 "open_questions": decision.open_questions, "tool_calls_used": run.tool_calls},
            )
            investigation.emit(
                AgentDecisionEvent,
                observation_id=inspected,
                reading=decision.reading,
                requests=records,
                open_questions=decision.open_questions,
                tool_calls_used=run.tool_calls,
                max_tool_calls=budget,
            )
            for record in records:
                if record.status != "accepted":
                    continue
                tool, arguments = self._registry.validate_call(record.tool, record.arguments, report, manifest)
                observation = await self._run_tool(
                    investigation, run, tool, arguments, record.arguments, step_id=f"follow-up-{record.request_id}",
                    reason=record.reason, request_id=record.request_id, cites=record.cites_observation_id,
                )
                unread.append(observation.observation_id)
        if unread or over_budget:
            run.open_questions += [
                OpenQuestion(text=f"{o} was never read by the agent: the budget was spent first.", source="unread_observation", observation_id=o)
                for o in unread
            ]
            questions = [q for q in run.open_questions if q.source != "agent"]
            investigation.audit_log.append(
                "budget_exhausted",
                {"tool_calls_used": run.tool_calls, "max_tool_calls": budget, "open_questions": [q.model_dump(mode="json") for q in questions]},
            )
            investigation.emit(BudgetExhaustedEvent, tool_calls_used=run.tool_calls, max_tool_calls=budget, open_questions=questions)

    def _follow_up_problem(
        self, run: "_Run", proposal: FollowUpProposal, earlier: list[FollowUpRequest], report: CapabilityReport, manifest: DatasetManifest
    ) -> str | None:
        """Why a follow-up request cannot run, or None. It must cite an observation of this investigation, name a
        registered tool with arguments valid for the dataset, and not repeat a call that ran or is about to."""
        if proposal.cites_observation not in {o.observation_id for o in run.observations}:
            return f"it cites {proposal.cites_observation!r}, which is not an observation of this investigation"
        try:
            self._registry.validate_call(proposal.tool, proposal.arguments, report, manifest)
        except ToolCallInvalid as invalid:
            return str(invalid)
        same = canonical_json({"tool": proposal.tool, "arguments": proposal.arguments})
        for observation in run.observations:
            if canonical_json({"tool": observation.tool.name, "arguments": observation.arguments}) == same:
                return f"the same call already ran as {observation.observation_id}"
        for record in earlier:
            if record.status == "accepted" and canonical_json({"tool": record.tool, "arguments": record.arguments}) == same:
                return f"it repeats {record.request_id}"
        return None

    # --- claims --------------------------------------------------------------------------------------------

    async def _draft_claims(self, investigation: Investigation, run: "_Run") -> list[Claim]:
        """One claim per audit result of the plan, drafted in parallel on Muse Spark Open and announced in plan order.
        Each claim cites the controls the agent ran on that result, and only those."""
        findings: dict[str, tuple[Tool, AuditResult]] = {}
        for observation in run.observations:
            if observation.request_id is None and isinstance(observation.artifact, AuditResult):
                findings.setdefault(observation.artifact.finding_id, (observation.tool, observation.artifact))
        drafted = await asyncio.gather(*(self._draft_claim(investigation, run, tool, finding) for tool, finding in findings.values()))
        claims = []
        for (_, finding), (claim, problems) in zip(findings.values(), drafted, strict=True):
            if claim is None:
                investigation.audit_log.append("claim_rejected", {"finding_id": finding.finding_id, "problems": problems})
                investigation.emit(ClaimRejectedEvent, finding_id=finding.finding_id, problems=problems)
                continue
            investigation.audit_log.append("claim_drafted", {"claim": claim.model_dump(mode="json")})
            investigation.emit(ClaimDraftedEvent, claim=claim)
            claims.append(claim)
        return claims

    async def _draft_claim(self, investigation: Investigation, run: "_Run", tool: Tool, finding: AuditResult) -> tuple[Claim | None, list[str]]:
        """Draft a claim, check it and allow one redraft. Its evidence status is the finding's computed label, never the
        model's; verification and review start pending and unreviewed."""
        gateway = self._gateway(investigation, self._recording(investigation))
        thinning, labels = run.controls_for(finding.finding_id)
        controls = {c.control_id: c for c in (thinning, labels) if c is not None}
        request, inputs = claim_request(investigation.state.question, finding, tool.spec(), list(controls.values()))
        try:
            draft, _ = await gateway.complete_json("claim_draft", request, inputs, ClaimDraft)
            problems = claim_problems(draft, finding, controls)
            if problems:
                request = redraft_request(request, draft.model_dump_json(), problems)
                draft, _ = await gateway.complete_json("claim_redraft", request, inputs, ClaimDraft)
                problems = claim_problems(draft, finding, controls)
                if problems:
                    return None, problems
        except (ModelOutputInvalid, ModelOutputTruncated) as unusable:
            # One unusable draft costs that claim, not the investigation: the other claims and the evidence stand.
            return None, [str(unusable)]
        claim = Claim(
            claim_id=new_id("clm"),
            investigation_id=investigation.investigation_id,
            dataset_id=finding.dataset_id,
            finding=FindingRef(finding_id=finding.finding_id, finding_kind=finding.finding_kind),
            text=draft.text,
            cited=draft.cited,
            controls=ClaimControls(
                random_thinning=thinning.control_id if thinning else None,
                label_sensitivity=labels.control_id if labels else None,
            ),
            evidence_status=finding.label,
        )
        return claim, []

    # --- verification ---------------------------------------------------------------------------------------

    async def _verify_claims(self, investigation: Investigation, run: "_Run", claims: list[Claim]) -> list[Claim]:
        """Verify every claim, record its injected variants for "Challenge the verifier", and show one injected variant
        (the changed effect of the first claim, chosen by kind, never by outcome) in the stream, labelled as injected.
        A failed claim stays in history; it is blocked only from the validated summary."""
        if not claims:
            return claims
        state = investigation.state
        findings = {o.artifact.finding_id: o.artifact for o in run.observations if isinstance(o.artifact, AuditResult)}
        controls = {o.artifact.control_id: o.artifact for o in run.observations
                    if isinstance(o.artifact, RandomThinningControl | LabelSensitivityCheck)}
        figures_dir = investigation.directory / "figures"
        figures, pngs = {}, {}
        for claim in claims:
            finding = findings.get(claim.finding.finding_id)
            if finding is None or any(f.finding_id == finding.finding_id for f in figures.values()):
                continue
            try:
                figure = await asyncio.to_thread(self._render_figure, finding, figures_dir)
            except Exception as error:  # noqa: BLE001 - no figure leaves the visual check unavailable, nothing more
                investigation.audit_log.append("figure_failed", {"finding_id": finding.finding_id, "error": f"{type(error).__name__}: {error}"})
                continue
            figures[figure.figure_id] = figure
            pngs[figure.figure_id] = (figures_dir / f"{finding.finding_id}.png").read_bytes()
        context = VerificationContext(
            datasets=self._store.dataset_ids(),
            findings=findings,
            controls=controls,
            figures=figures,
            figure_png=pngs,
            label_rules=self._store.label_rules(state.dataset_id),
            load_sections=lambda ids, rule: [self._store.load_section(i, rule) for i in ids],
            gateway=self._gateway(investigation, self._recording(investigation)),
        )
        verified_claims = []
        challenges_dir = investigation.directory / "challenges"
        challenges_dir.mkdir(exist_ok=True)
        for index, claim in enumerate(claims):
            finding = findings.get(claim.finding.finding_id)
            if finding is not None:  # the recompute reads the molecule tables: keep it off the event loop
                await asyncio.to_thread(context.recompute, finding)
                for control in controls.values():
                    if isinstance(control, LabelSensitivityCheck) and any(a.finding_id == finding.finding_id for a in control.arms):
                        for arm in control.arms:
                            await asyncio.to_thread(context.recompute, finding, arm.label_rule_id)
            verified, verification = await verify_claim(claim, context)
            self._announce_verification(investigation, verified, verification)
            verified_claims.append(verified)
            if finding is None:
                continue
            other = next((f.figure_id for f in figures.values() if f.finding_id != finding.finding_id), None)
            challenges = await challenge(verified, verification, context, other_figure_id=other)
            (challenges_dir / f"{claim.claim_id}.json").write_text(challenges.model_dump_json(indent=1), encoding="utf-8")
            investigation.audit_log.append(
                "claim_challenges_recorded",
                {"claim_id": claim.claim_id, "claim_version": claim.version,
                 "variants": [{"kind": v.kind.value, "verification_status": v.verification.verification_status.value,
                               "detected": v.detected, "new_reasons": v.new_reasons} for v in challenges.variants]},
            )
            if index == 0:
                shown = next(v for v in challenges.variants if v.kind == InjectedErrorKind.CHANGED_EFFECT)
                self._announce_verification(investigation, shown.claim, shown.verification)
        return verified_claims

    def _render_figure(self, finding: AuditResult, out_dir: Path):
        region = next((r for r in finding.evidence_regions if r.rank == 1), None)
        sections = {}
        if region is not None:
            sections[region.region.section_id] = self._store.load_section(region.region.section_id, finding.population.label_rule_id)
        title = f"{' / '.join(finding.genes) if finding.measure != 'co_expression_score' else 'Co-expression score'} in cells labelled " \
                f"{finding.population.cell_type} ({finding.population.label_rule_id})"
        return render_composite_figure(finding, sections, out_dir, title=title)

    def _announce_verification(self, investigation: Investigation, claim: Claim, verification) -> None:
        investigation.audit_log.append(
            "claim_verified",
            {"claim_id": claim.claim_id, "claim_version": claim.version, "finding_id": claim.finding.finding_id,
             "injected": claim.injected.model_dump(mode="json"), "verification_status": verification.verification_status.value,
             "checks": {c.kind: c.status for c in verification.checks}, "reasons": reasons_of(verification),
             "figure_id": verification.figure.figure_id if verification.figure else None},
        )
        investigation.emit(ClaimVerifiedEvent, claim=claim, verification=verification)

    def _export(self, investigation: Investigation, claims: list[Claim], open_questions: list[OpenQuestion]) -> PackageInfo:
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
            open_questions=open_questions,
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
            open_questions=open_questions,
        )


@dataclass
class _Observation:
    """A tool's result as the agent receives it."""

    observation_id: str
    step_id: str
    tool: Tool
    arguments: dict[str, Any]
    request_id: str | None
    cites_observation_id: str | None
    reason: str
    artifact: Any = None
    summary: str | None = None
    error: str | None = None

    def view(self) -> dict[str, Any]:
        """The observation as the agent model reads it, with no run-specific ids, so the request is the same every run."""
        view: dict[str, Any] = {
            "observation_id": self.observation_id,
            "tool": self.tool.name,
            "arguments": self.arguments,
            "origin": "plan" if self.request_id is None else "follow_up",
        }
        if self.request_id is not None:
            view.update(request_id=self.request_id, cites_observation_id=self.cites_observation_id, reason=self.reason)
        if self.error is not None:
            view["error"] = self.error
        elif self.artifact is not None:
            view.update(artifact_id=_artifact_id(self.artifact), summary=self.summary, result=observation_view(self.artifact))
        return view


@dataclass
class _Run:
    """One execution in memory: the observations in the order they arrived, and the requests the agent made."""

    plan: Plan
    observations: list[_Observation] = field(default_factory=list)
    requests: int = 0
    open_questions: list[OpenQuestion] = field(default_factory=list)

    @property
    def tool_calls(self) -> int:
        return len(self.observations)

    def controls_for(self, finding_id: str) -> tuple[RandomThinningControl | None, LabelSensitivityCheck | None]:
        """The controls the agent ran on this finding: a random-thinning control of the same audit, and a
        label-sensitivity check one of whose arms is that audit."""
        thinning = next(
            (o.artifact for o in self.observations if isinstance(o.artifact, RandomThinningControl) and o.artifact.finding_id == finding_id),
            None,
        )
        labels = next(
            (o.artifact for o in self.observations
             if isinstance(o.artifact, LabelSensitivityCheck) and any(arm.finding_id == finding_id for arm in o.artifact.arms)),
            None,
        )
        return thinning, labels


def _artifact_id(artifact: Any) -> str:
    for field_name in ("control_id", "finding_id", "artifact_id"):
        if isinstance(getattr(artifact, field_name, None), str):
            return getattr(artifact, field_name)
    raise TypeError(f"a tool returned an artifact without an id: {type(artifact).__name__}")
