"""The investigation orchestrator: a bounded state machine that runs independently of any HTTP connection.

question -> plan proposed -> (approval) -> tool steps -> claim drafted -> package ready

Work runs in tasks the orchestrator owns, so a client may disconnect and reconnect (with `after_seq`)
without affecting it. Every state change is persisted before it is announced.
"""

import asyncio
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..contracts import (
    ErrorEvent,
    InvestigationStatus,
    PlanApprovedEvent,
    PlanProposal,
    PlanProposedEvent,
    Recording,
    RunMode,
    checksum,
)
from ..data import DatasetStore
from ..gateway import GatewayError, ModelGateway, RecordingLibrary, ReplaySource, StoredResponseMissing, normalise_question
from .errors import InvestigationError, RunModeUnavailable
from .investigation import Investigation
from .prompts import plan_request
from .tools import ToolRegistry


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
    ) -> None:
        self._store = store
        self._recordings = recordings
        self._registry = registry
        self._root = Path(investigations_dir)
        self._dataset_id = dataset_id
        self._clock = clock
        self._investigations: dict[str, Investigation] = {}
        self._gateways: dict[str, ModelGateway] = {}
        self._tasks: set[asyncio.Task[None]] = set()

    def start(self, question: str, run_mode: RunMode) -> Investigation:
        """Create and persist an investigation, then propose its plan in the background."""
        question = normalise_question(question)
        recording = self._recordings.for_question(question)
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
        """An investigation by id, from memory or, after a restart, from its directory."""
        if investigation_id not in self._investigations:
            self._investigations[investigation_id] = Investigation.load(self._root, investigation_id, self._clock)
        return self._investigations[investigation_id]

    async def shutdown(self) -> None:
        for task in list(self._tasks):
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)

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
        run_mode = investigation.state.run_mode
        if run_mode == "live":
            raise RunModeUnavailable("Live runs arrive with ticket 03, behind a passcode and a daily spend budget.")
        if run_mode == "immutable_replay":
            raise RunModeUnavailable("Immutable replay of recorded events arrives with ticket 03; use cached_tool_rerun.")
        if recording is None:
            raise StoredResponseMissing(
                "No stored model responses answer this question. A cached tool rerun can only ask recorded questions; "
                "live runs arrive with ticket 03."
            )
        gateway = self._gateways.get(investigation.investigation_id)
        if gateway is None:
            gateway = self._gateways[investigation.investigation_id] = ModelGateway(ReplaySource(recording), self._clock)
        return gateway

    async def _propose_plan(self, investigation: Investigation, recording: Recording | None) -> None:
        gateway = self._gateway(investigation, recording)
        state = investigation.state
        request, inputs = plan_request(state.question, self._store.capability_report(state.dataset_id), self._registry.specs())
        try:
            proposal, call = await gateway.complete_json("plan", request, inputs, PlanProposal)
        except GatewayError as error:
            if error.record is not None:
                investigation.audit_log.append("model_call", error.record.model_dump(mode="json"))
            raise
        investigation.audit_log.append("model_call", call.model_dump(mode="json"))
        plan = self._registry.plan_from(
            proposal,
            investigation_id=investigation.investigation_id,
            question=state.question,
            dataset_id=state.dataset_id,
            proposed_by=request.model,
        )
        investigation.audit_log.append("plan_proposed", {"plan": plan.model_dump(mode="json")})
        investigation.emit(PlanProposedEvent, status=InvestigationStatus.AWAITING_APPROVAL, plan=plan)
