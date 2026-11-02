"""Plan contracts: the model's proposal and the plan the researcher approves and freezes."""

from datetime import datetime
from typing import Any, Literal

from .base import SCHEMA_VERSION, ConditionName, Contract, Contrast


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
    budget: Budget
    proposed_by: str
    status: Literal["proposed", "approved", "rejected"] = "proposed"
    approved_at: datetime | None = None
    plan_hash: str | None = None
