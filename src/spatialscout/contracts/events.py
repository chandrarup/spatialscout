"""Investigation events: a discriminated union on `type`, streamed over SSE in `seq` order.

Add a new event by defining a model with a unique `type` literal and adding it to `InvestigationEvent`.
"""

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import Field

from .agent import FollowUpRequest, OpenQuestion
from .base import Contract, EvidenceStatus
from .claim import Claim
from .model_call import ModelCallRecord
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


class PlanRejectedEvent(EventBase):
    """A plan turned down. By the validator: it names a tool outside the registry, invalid arguments or an analysis
    the capability report does not support; the planner gets one re-plan. By the researcher: the investigation ends
    and nothing runs."""

    type: Literal["plan_rejected"] = "plan_rejected"
    by: Literal["validator", "researcher"]
    attempt: int = Field(ge=1, description="1 for the first proposal, 2 for the re-plan.")
    reason: str
    tools: list[str] = Field(default_factory=list, description="The tools the rejected proposal named.")
    plan_id: str | None = None


class ToolStartedEvent(EventBase):
    """A tool call starting. A plan step has no request; a follow-up names its request and the observation it cites."""

    type: Literal["tool_started"] = "tool_started"
    step_id: str
    tool: str
    arguments: dict[str, Any]
    observation_id: str | None = Field(default=None, description="The observation this call will produce.")
    request_id: str | None = None
    cites_observation_id: str | None = None
    reason: str | None = Field(default=None, description="A plan step's rationale, or the agent's reason for a follow-up.")


class ToolFinishedEvent(EventBase):
    type: Literal["tool_finished"] = "tool_finished"
    step_id: str
    tool: str
    artifact_id: str
    summary: str
    observation_id: str | None = None
    label: EvidenceStatus | None = Field(default=None, description="The artifact's computed evidence label, when it has one.")


class ToolFailedEvent(EventBase):
    """A tool call that raised instead of returning an artifact. The failure is itself an observation the agent reads."""

    type: Literal["tool_failed"] = "tool_failed"
    step_id: str
    tool: str
    observation_id: str
    error: str


class AgentDecisionEvent(EventBase):
    """Muse Spark 1.3 after reading one observation: what it read, the follow-ups it requested (each citing an
    observation, with its status) and the questions it left open."""

    type: Literal["agent_decision"] = "agent_decision"
    observation_id: str
    reading: str
    requests: list[FollowUpRequest]
    open_questions: list[str] = Field(default_factory=list)
    tool_calls_used: int
    max_tool_calls: int


class BudgetExhaustedEvent(EventBase):
    """The plan's tool-call budget is spent: the investigation drafts claims from the evidence it has and reports
    what it could not settle."""

    type: Literal["budget_exhausted"] = "budget_exhausted"
    tool_calls_used: int
    max_tool_calls: int
    open_questions: list[OpenQuestion]


class ClaimRejectedEvent(EventBase):
    """A claim draft that failed validation even after one redraft. No claim is made from it."""

    type: Literal["claim_rejected"] = "claim_rejected"
    finding_id: str
    problems: list[str]


class ClaimDraftedEvent(EventBase):
    type: Literal["claim_drafted"] = "claim_drafted"
    claim: Claim


class PackageReadyEvent(EventBase):
    type: Literal["package_ready"] = "package_ready"
    package: PackageInfo


class ModelCallEvent(EventBase):
    """Telemetry for one model call: provider, model, purpose, latency, tokens, estimated cost, whether the
    response was live or stored, and the run mode. Never carries keys or prompt text."""

    type: Literal["model_call"] = "model_call"
    call: ModelCallRecord


class ErrorEvent(EventBase):
    type: Literal["error"] = "error"
    code: str
    message: str


InvestigationEvent = Annotated[
    PlanProposedEvent
    | PlanApprovedEvent
    | PlanRejectedEvent
    | ToolStartedEvent
    | ToolFinishedEvent
    | ToolFailedEvent
    | AgentDecisionEvent
    | BudgetExhaustedEvent
    | ClaimDraftedEvent
    | ClaimRejectedEvent
    | PackageReadyEvent
    | ModelCallEvent
    | ErrorEvent,
    Field(discriminator="type"),
]
