"""The tool registry: the fixed set of deterministic analysis operations the agent may call.

Add a tool by defining its arguments contract, a run function over a `ToolContext`, and a one-line summary,
then register it. A tool's `version` is part of every cache key built from its outputs, so bump it whenever
its behaviour changes.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from pydantic import Field, ValidationError, field_validator

from ..contracts import AuditResult, ConditionName, Contract, Plan, PlanProposal, PlanStep, ToolSpec, new_id
from ..contracts.plan import Budget
from ..data import DatasetStore
from ..engine import IMPLEMENTED_CONDITIONS, audit_population
from .errors import PlanInvalid


@dataclass(frozen=True)
class ToolContext:
    store: DatasetStore


@dataclass(frozen=True)
class Tool:
    name: str
    version: str
    description: str
    arguments: type[Contract]
    run: Callable[[Any, ToolContext], Contract]
    summarize: Callable[[Any], str]

    def spec(self) -> ToolSpec:
        return ToolSpec(name=self.name, version=self.version, description=self.description, arguments_schema=self.arguments.model_json_schema())


class AuditPopulationArguments(Contract):
    section_ids: list[str] = Field(min_length=1)
    cell_type: str
    genes: list[str] = Field(min_length=1, max_length=1, description="One gene; gene sets and pairs arrive with ticket 05.")
    conditions: list[ConditionName] = Field(min_length=2)

    @field_validator("conditions")
    @classmethod
    def _computable(cls, conditions: list[ConditionName]) -> list[ConditionName]:
        if ConditionName.DEFAULT not in conditions:
            raise ValueError("the default condition is required: retention is measured against it")
        missing = [c.value for c in conditions if c not in IMPLEMENTED_CONDITIONS]
        if missing:
            raise ValueError(f"conditions not implemented yet: {', '.join(missing)}")
        return conditions


def _run_audit_population(arguments: AuditPopulationArguments, context: ToolContext) -> AuditResult:
    sections = [context.store.load_section(section_id) for section_id in arguments.section_ids]
    return audit_population(sections, arguments.cell_type, arguments.genes, arguments.conditions)


def _summarize_audit_result(result: AuditResult) -> str:
    gene = "/".join(result.genes)
    parts = []
    for section in result.sections:
        default = next(v for v in section.conditions if v.condition == ConditionName.DEFAULT)
        for value in section.conditions:
            if value.condition == ConditionName.DEFAULT:
                continue
            retention = "n/a" if value.retention is None else f"{value.retention:.0%}"
            parts.append(
                f"{section.section_id}, {value.condition.value}: keeps {value.molecules} of {default.molecules} {gene} "
                f"molecules in the {section.cells_labelled} cells labelled {result.population.cell_type} (retention {retention})"
            )
    return "; ".join(parts) + f". Evidence label: {result.label.value.replace('_', ' ')}."


AUDIT_POPULATION = Tool(
    name="audit_population",
    version="1",
    description=(
        "Audit one gene's presence in one cell population across assignment conditions, per section: molecules "
        "kept, retention against the default condition, share of cells expressing, and nuclear-overlap share."
    ),
    arguments=AuditPopulationArguments,
    run=_run_audit_population,
    summarize=_summarize_audit_result,
)


class ToolRegistry:
    def __init__(self, tools: Sequence[Tool]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    def specs(self) -> list[ToolSpec]:
        return [tool.spec() for tool in self._tools.values()]

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise PlanInvalid(f"the plan names a tool that is not in the registry: {name!r}")
        return self._tools[name]

    def plan_from(self, proposal: PlanProposal, *, investigation_id: str, question: str, dataset_id: str, proposed_by: str) -> Plan:
        """Check every proposed step against the registry and turn the proposal into a plan to approve."""
        steps = []
        for index, step in enumerate(proposal.steps, start=1):
            tool = self.get(step.tool)
            try:
                tool.arguments.model_validate(step.arguments)
            except ValidationError as error:
                raise PlanInvalid(f"step {index} ({step.tool}) has invalid arguments: {error.errors()[0]['msg']}") from error
            steps.append(PlanStep(step_id=f"step-{index}", tool=step.tool, arguments=step.arguments, rationale=step.rationale))
        if not steps:
            raise PlanInvalid("the plan has no steps")
        return Plan(
            plan_id=new_id("pln"),
            investigation_id=investigation_id,
            question=question,
            dataset_id=dataset_id,
            summary=proposal.summary,
            contrast=proposal.contrast,
            cell_types=proposal.cell_types,
            conditions=proposal.conditions,
            steps=steps,
            budget=Budget(),
            proposed_by=proposed_by,
        )


DEFAULT_REGISTRY = ToolRegistry([AUDIT_POPULATION])
