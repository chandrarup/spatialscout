"""Plan contracts: the model's proposal and the plan the researcher approves and freezes."""

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from .base import SCHEMA_VERSION, ConditionName, Contract, Contrast
from .verdict import SubClaim


class ToolSpec(Contract):
    """A tool as the planner sees it in the registry."""

    name: str
    version: str
    description: str
    arguments_schema: dict[str, Any]


class ProposedStep(Contract):
    tool: str
    arguments: dict[str, Any]
    rationale: str


class PlanProposal(Contract):
    """The planner model's structured output, before it is checked against the tool registry."""

    summary: str
    contrast: Contrast | None
    cell_types: list[str]
    conditions: list[ConditionName]
    steps: list[ProposedStep]
    sub_claims: list[SubClaim] = Field(default_factory=list, description="The question split into testable sub-claims, each with the hypothesis's prediction.")


class PlanStep(Contract):
    step_id: str
    tool: str
    arguments: dict[str, Any]
    rationale: str


class Budget(Contract):
    max_tool_calls: int = 12


class Plan(Contract):
    """The ordered tool steps proposed for a question; frozen once approved (its hash is then recorded)."""

    schema_version: str = SCHEMA_VERSION
    plan_id: str
    investigation_id: str
    question: str
    dataset_id: str
    summary: str
    contrast: Contrast | None
    cell_types: list[str]
    conditions: list[ConditionName]
    steps: list[PlanStep]
    sub_claims: list[SubClaim] = Field(default_factory=list)
    budget: Budget
    proposed_by: str
    status: Literal["proposed", "approved", "rejected"] = "proposed"
    approved_at_utc: datetime | None = None
    plan_hash: str | None = Field(default=None, description="sha256 of the proposed plan's canonical JSON, set at approval.")
