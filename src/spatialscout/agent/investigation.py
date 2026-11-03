"""One persisted investigation: its state, its events and its audit log, in its own directory.

Layout of `<investigations_dir>/<investigation_id>/`:
- `state.json`: the InvestigationState, replaced atomically on every change
- `events.jsonl`: one InvestigationEvent per line; `seq` starts at 1 and rises by one per event
- `audit_log.jsonl`: the hash-linked audit log
- `artifacts/`: tool outputs as JSON, named by artifact id
- `package.zip`: the evidence package, once built

Events are written and flushed before any stream is woken, so a client that reconnects with `after_seq`
always finds every event it missed.
"""

import asyncio
import os
import re
from collections.abc import AsyncIterator, Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from ..audit import AuditLog
from ..contracts import (
    TERMINAL_STATUSES,
    ClaimDraftedEvent,
    EventBase,
    InvestigationEvent,
    InvestigationSnapshot,
    InvestigationState,
    InvestigationStatus,
    PackageReadyEvent,
    Plan,
    PlanApprovedEvent,
    PlanProposedEvent,
    ReplayInfo,
    RunMode,
    new_id,
)
from .errors import UnknownInvestigation

INVESTIGATION_ID = re.compile(r"^inv-[0-9a-f]{12}$")
_EVENT = TypeAdapter(InvestigationEvent)


class Investigation:
    def __init__(self, directory: Path, state: InvestigationState, events: list[Any], clock: Callable[[], datetime]) -> None:
        self.directory = directory
        self.state = state
        self.events: list[Any] = events
        self.audit_log = AuditLog(directory / "audit_log.jsonl", state.investigation_id, clock)
        self._clock = clock
        self._changed = asyncio.Event()

    @classmethod
    def create(
        cls, root: Path, question: str, run_mode: RunMode, dataset_id: str, replay: ReplayInfo | None, clock: Callable[[], datetime]
    ) -> "Investigation":
        investigation_id = new_id("inv")
        directory = Path(root) / investigation_id
        directory.mkdir(parents=True)
        now = clock()
        state = InvestigationState(
            investigation_id=investigation_id,
            question=question,
            run_mode=run_mode,
            status=InvestigationStatus.PLANNING,
            dataset_id=dataset_id,
            replay=replay,
            created_at_utc=now,
            updated_at_utc=now,
        )
        (directory / "events.jsonl").touch()
        investigation = cls(directory, state, [], clock)
        investigation._write_state()
        return investigation

    @classmethod
    def load(cls, root: Path, investigation_id: str, clock: Callable[[], datetime]) -> "Investigation":
        directory = Path(root) / investigation_id
        if not INVESTIGATION_ID.match(investigation_id) or not (directory / "state.json").is_file():
            raise UnknownInvestigation(investigation_id)
        state = InvestigationState.model_validate_json((directory / "state.json").read_text(encoding="utf-8"))
        lines = (directory / "events.jsonl").read_text(encoding="utf-8").splitlines()
        return cls(directory, state, [_EVENT.validate_json(line) for line in lines if line], clock)

    @property
    def investigation_id(self) -> str:
        return self.state.investigation_id

    @property
    def finished(self) -> bool:
        return self.state.status in TERMINAL_STATUSES

    def emit(self, event_type: type[EventBase], status: InvestigationStatus | None = None, **fields: Any) -> Any:
        """Record an event (and optionally the status it moves to), then wake every waiting stream."""
        now = self._clock()
        event = event_type(seq=self.state.last_seq + 1, investigation_id=self.investigation_id, recorded_at_utc=now, **fields)
        with (self.directory / "events.jsonl").open("a", encoding="utf-8") as events_file:
            events_file.write(event.model_dump_json() + "\n")
            events_file.flush()
        self.events.append(event)
        changes: dict[str, Any] = {"last_seq": event.seq, "updated_at_utc": now}
        if status is not None:
            changes["status"] = status
            if status in TERMINAL_STATUSES:
                changes["finished_at_utc"] = now
        self.update_state(**changes)
        changed, self._changed = self._changed, asyncio.Event()
        changed.set()
        return event

    def update_state(self, **changes: Any) -> None:
        self.state = self.state.model_copy(update=changes)
        self._write_state()

    def _write_state(self) -> None:
        temporary = self.directory / "state.json.tmp"
        temporary.write_text(self.state.model_dump_json(indent=2), encoding="utf-8")
        os.replace(temporary, self.directory / "state.json")

    async def events_after(self, after_seq: int, window_seconds: float | None = None) -> AsyncIterator[Any]:
        """Every event with `seq > after_seq`, in order, waiting for new ones until the investigation finishes or,
        given `window_seconds`, until that window closes. Events already recorded are always delivered first."""
        loop = asyncio.get_running_loop()
        deadline = None if window_seconds is None else loop.time() + window_seconds
        position = max(after_seq, 0)  # the event at index i has seq i + 1
        while True:
            changed = self._changed
            while position < len(self.events):
                yield self.events[position]
                position += 1
            if self.finished:
                return
            if deadline is None:
                await changed.wait()
                continue
            remaining = deadline - loop.time()
            if remaining <= 0:
                return
            try:
                await asyncio.wait_for(changed.wait(), remaining)
            except TimeoutError:
                return

    def plan(self) -> Plan | None:
        plan = None
        for event in self.events:
            if isinstance(event, PlanProposedEvent):
                plan = event.plan
            elif isinstance(event, PlanApprovedEvent) and plan is not None:
                plan = plan.model_copy(update={"status": "approved", "plan_hash": event.plan_hash, "approved_at_utc": event.recorded_at_utc})
        return plan

    def snapshot(self) -> InvestigationSnapshot:
        packages = [e.package for e in self.events if isinstance(e, PackageReadyEvent)]
        return InvestigationSnapshot(
            investigation_id=self.investigation_id,
            question=self.state.question,
            status=self.state.status,
            run_mode=self.state.run_mode,
            replay=self.state.replay,
            dataset_id=self.state.dataset_id,
            plan=self.plan(),
            claims=[e.claim for e in self.events if isinstance(e, ClaimDraftedEvent)],
            package=packages[-1] if packages else None,
            events=list(self.events),
        )
