"""Agent-loop contracts: what Muse Spark 1.3 decides after reading each observation, and the follow-up requests it
makes within the plan's tool-call budget (spec "Investigation orchestrator", steps 5 and 6).

An observation is a tool's result as the agent receives it. Its id is `obs-<n>`, numbered in the order the tools ran,
so the same run builds the same model requests (and cache keys) every time. Every follow-up request cites the
observation that prompted it; the orchestrator runs only what the agent requests and never a control on its behalf.
"""

from typing import Any, Literal

from pydantic import Field

from .base import Contract


class FollowUpProposal(Contract):
    """One follow-up tool call as the agent model proposes it, before it is checked against the registry."""

    tool: str
    arguments: dict[str, Any]
    cites_observation: str = Field(description="The id of the observation that prompted this request, such as obs-1.")
    reason: str = Field(description="Why this observation calls for this tool, in one or two sentences.")


class FollowUpDecision(Contract):
    """The agent model's structured output after reading one observation."""

    reading: str = Field(description="What the agent reads in the observation, in one to three sentences.")
    requests: list[FollowUpProposal] = Field(description="Follow-up tool calls; empty when the observation needs none.")
    open_questions: list[str] = Field(
        default_factory=list, description="Questions the evidence leaves open that the registry's tools cannot answer."
    )


FollowUpStatus = Literal["accepted", "rejected", "over_budget"]


class FollowUpRequest(Contract):
    """A follow-up request as the orchestrator recorded it: accepted (and run), rejected (with the reason) or over
    budget (not run, and reported as an open question)."""

    request_id: str = Field(description="req-<n>, numbered in the order the agent made its requests.")
    tool: str
    arguments: dict[str, Any]
    cites_observation_id: str
    reason: str
    status: FollowUpStatus
    rejection_reason: str | None = None


class OpenQuestion(Contract):
    """Something the investigation could not settle: a follow-up the budget did not allow, an observation the agent
    never read because the budget ran out, or a question the agent raised."""

    text: str
    source: Literal["over_budget_request", "unread_observation", "agent"]
    observation_id: str | None = None
    request_id: str | None = None
