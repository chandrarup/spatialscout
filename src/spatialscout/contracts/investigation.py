"""Investigation contracts: persisted state, HTTP snapshots and the serving mode."""

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from .base import SCHEMA_VERSION, Contract, RunMode
from .claim import Claim
from .events import InvestigationEvent
from .model_call import ReplayInfo
from .package import PackageInfo
from .plan import Plan


class InvestigationStatus(StrEnum):
    PLANNING = "planning"
    AWAITING_APPROVAL = "awaiting_approval"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


TERMINAL_STATUSES = frozenset({InvestigationStatus.COMPLETE, InvestigationStatus.FAILED})


class InvestigationState(Contract):
    """state.json in the investigation's directory; events.jsonl beside it holds every event."""

    schema_version: str = SCHEMA_VERSION
    investigation_id: str
    question: str
    run_mode: RunMode
    status: InvestigationStatus
    dataset_id: str
    replay: ReplayInfo | None
    approved_plan_hash: str | None = None
    created_at_utc: datetime
    updated_at_utc: datetime
    approved_at_utc: datetime | None = None
    finished_at_utc: datetime | None = None
    last_seq: int = 0


class StartInvestigationRequest(Contract):
    question: str = Field(min_length=1, max_length=2000)
    run_mode: RunMode = "cached_tool_rerun"


class InvestigationSnapshot(Contract):
    """The current state of one investigation, including every event emitted so far."""

    investigation_id: str
    question: str
    status: InvestigationStatus
    run_mode: RunMode
    replay: ReplayInfo | None
    dataset_id: str
    plan: Plan | None
    claims: list[Claim]
    package: PackageInfo | None
    events: list[InvestigationEvent]


class ModeInfo(Contract):
    """How the server answers questions. Live mode arrives with ticket 03."""

    default_run_mode: RunMode
    available_run_modes: list[RunMode]
    recordings: list[ReplayInfo]
