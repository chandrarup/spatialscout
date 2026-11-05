"""Investigation contracts: persisted state, HTTP snapshots and the serving mode."""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import Field, field_validator

from .base import SCHEMA_VERSION, Contract, RunMode
from .claim import Claim
from .finding import Region
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
    REJECTED = "rejected"
    """The researcher rejected the plan; nothing ran."""


TERMINAL_STATUSES = frozenset({InvestigationStatus.COMPLETE, InvestigationStatus.FAILED, InvestigationStatus.REJECTED})


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
    regions: list[Region] = Field(default_factory=list, description="Regions the researcher drew in the viewer, kept as context.")


class StartInvestigationRequest(Contract):
    question: str = Field(min_length=1, max_length=2000)
    run_mode: RunMode = "cached_tool_rerun"
    dataset_id: str | None = Field(
        default=None, description="The dataset to investigate; the server's default when omitted. A recording names its own."
    )
    regions: list[Region] = Field(
        default_factory=list,
        max_length=2,
        description=(
            "Regions the researcher drew in the dual-section viewer (one per section), kept with the investigation as "
            "context and shown beside its verdicts. Each must lie on a section of the investigated dataset. They do not "
            "scope the analysis or reach any model prompt. Ignored by immutable replay, which returns a recorded investigation."
        ),
    )

    @field_validator("regions")
    @classmethod
    def _regions_have_area(cls, regions: list[Region]) -> list[Region]:
        for region in regions:
            if not (region.x1 > region.x0 and region.y1 > region.y0):
                raise ValueError(f"region on {region.section_id} needs x1 > x0 and y1 > y0")
        return regions


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
    approved_plan_hash: str | None = None
    regions: list[Region] = Field(default_factory=list, description="Regions the researcher drew in the viewer, kept as context.")


class ModeInfo(Contract):
    """How the server answers questions. Live runs arrive with ticket 03."""

    dataset_id: str
    default_run_mode: RunMode
    available_run_modes: list[RunMode]
    recordings: list[ReplayInfo]
    live_access: list[Literal["owner", "trial", "byok"]] = Field(
        default_factory=list, description="Who may start a live run: the owner's passcode, the open trial, or bring-your-own-key."
    )
    trial_remaining_usd: float | None = Field(default=None, description="Left in today's live trial budget; null when no trial is open.")
