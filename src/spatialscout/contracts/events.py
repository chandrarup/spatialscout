"""Investigation events: a discriminated union on `type`, streamed over SSE in `seq` order.

Add a new event by defining a model with a unique `type` literal and adding it to `InvestigationEvent`.
"""

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import Field

from .base import Contract
from .claim import Claim
from .package import PackageInfo
from .plan import Plan


class EventBase(Contract):
    """Fields every event carries. `seq` starts at 1 and increases by one per event within an
    investigation; `recorded_at_utc` is when the event was first recorded and never changes on replay."""

    seq: int = Field(ge=1)
    investigation_id: str
    recorded_at_utc: datetime


class PlanProposedEvent(EventBase):
    type: Literal["plan_proposed"] = "plan_proposed"
    plan: Plan


class PlanApprovedEvent(EventBase):
    type: Literal["plan_approved"] = "plan_approved"
    plan_id: str
    plan_hash: str


class ToolStartedEvent(EventBase):
    type: Literal["tool_started"] = "tool_started"
    step_id: str
    tool: str
    arguments: dict[str, Any]


class ToolFinishedEvent(EventBase):
    type: Literal["tool_finished"] = "tool_finished"
    step_id: str
    tool: str
    artifact_id: str
    summary: str


class ClaimDraftedEvent(EventBase):
    type: Literal["claim_drafted"] = "claim_drafted"
    claim: Claim


class PackageReadyEvent(EventBase):
    type: Literal["package_ready"] = "package_ready"
    package: PackageInfo


class ErrorEvent(EventBase):
    type: Literal["error"] = "error"
    code: str
    message: str


InvestigationEvent = Annotated[
    PlanProposedEvent
    | PlanApprovedEvent
    | ToolStartedEvent
    | ToolFinishedEvent
    | ClaimDraftedEvent
    | PackageReadyEvent
    | ErrorEvent,
    Field(discriminator="type"),
]
