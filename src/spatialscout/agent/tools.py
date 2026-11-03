"""The tool registry: the fixed set of deterministic analysis operations the agent may call.

Add a tool by defining its arguments contract, a run function over a `ToolContext`, and a one-line summary,
then register it. A tool's `version` is part of every cache key built from its outputs, so bump it whenever
its behaviour changes.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import Field, ValidationError, field_validator, model_validator

from ..contracts import (
    AuditResult,
    ConditionName,
    Contract,
    LabelSensitivityCheck,
    Plan,
    PlanProposal,
    PlanStep,
    PooledConditionValue,
    RandomThinningControl,
    Region,
    ToolSpec,
    new_id,
)
from ..contracts.plan import Budget
from ..data import FULL_PANEL_RULE, NPHS1_ANCHORED_RULE, DatasetStore
from ..engine import IMPLEMENTED_CONDITIONS, audit_population, label_sensitivity_check, random_thinning_control
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
    genes: list[str] = Field(
        default_factory=list,
        description="One gene (share expressing) or several (presence of any). For the co-expression score, empty "
        "for every frozen exclusive marker pair, or one pair.",
    )
    conditions: list[ConditionName] = Field(min_length=2)
    measure: Literal["share_expressing", "gene_set_share_expressing", "co_expression_score"] | None = Field(
        default=None, description="Inferred from the genes when omitted."
    )
    label_rule_id: str | None = Field(default=None, description="The frozen label rule; the dataset's default when omitted.")
    roi: Region | None = Field(default=None, description="A box on one of the sections; the audit then covers only that box.")

    @field_validator("conditions")
    @classmethod
    def _computable(cls, conditions: list[ConditionName]) -> list[ConditionName]:
        if ConditionName.DEFAULT not in conditions:
            raise ValueError("the default condition is required: retention is measured against it")
        missing = [c.value for c in conditions if c not in IMPLEMENTED_CONDITIONS]
        if missing:
            raise ValueError(f"conditions not implemented yet: {', '.join(missing)}")
        return conditions

    @model_validator(mode="after")
    def _genes_fit_the_measure(self) -> "AuditPopulationArguments":
        if self.measure != "co_expression_score" and not self.genes:
            raise ValueError("a presence measure needs at least one gene")
        if self.measure == "co_expression_score" and len(self.genes) not in (0, 2):
            raise ValueError("the co-expression score takes no genes (every frozen pair) or one pair")
        return self


def _sections(context: ToolContext, section_ids: Sequence[str], label_rule_id: str | None, roi: Region | None):
    """Load the sections, leaving out any that duplicates another (counted once), with their groups. With an ROI,
    only the ROI's section is audited."""
    if roi is not None:
        section_ids = [roi.section_id]
    groups, left_out, loaded = {}, {}, []
    for section_id in section_ids:
        info = context.store.section_info(section_id)
        if info.duplicate_of is not None:
            left_out[section_id] = f"duplicate_of {info.duplicate_of}"
            continue
        if info.group:
            groups[section_id] = info.group
        loaded.append(context.store.load_section(section_id, label_rule_id))
    return loaded, groups, left_out


def _audit(arguments: AuditPopulationArguments, context: ToolContext, label_rule_id: str | None = None) -> AuditResult:
    sections, groups, left_out = _sections(context, arguments.section_ids, label_rule_id or arguments.label_rule_id, arguments.roi)
    return audit_population(
        sections,
        arguments.cell_type,
        arguments.genes,
        arguments.conditions,
        measure=arguments.measure,
        section_groups=groups,
        sections_left_out=left_out,
        roi=arguments.roi,
    )


def _run_audit_population(arguments: AuditPopulationArguments, context: ToolContext) -> AuditResult:
    return _audit(arguments, context)


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1%}"


def _summarize_pooled(pooled: Sequence[PooledConditionValue]) -> str:
    return "; ".join(
        f"{p.condition.value}: observed {_pct(p.observed_value)}, retention {_pct(p.retention)}, home-matched "
        f"expectation {_pct(p.expectation_home_matched)}, cell-matched {_pct(p.expectation_cell_matched)}"
        for p in pooled
    )


def _summarize_audit_result(result: AuditResult) -> str:
    gene = "/".join(result.genes) if result.measure != "co_expression_score" else f"{len(result.gene_pairs)} marker pairs"
    where = f" inside the ROI on {result.roi.section_id}" if result.roi else ""
    if result.eligible_section_ids:
        return (
            f"{result.measure.replace('_', ' ')} of {gene} in cells labelled {result.population.cell_type} "
            f"({result.population.label_rule_id}){where}, pooled over {len(result.eligible_section_ids)} eligible of "
            f"{len(result.sections)} sections: {_summarize_pooled(result.pooled)}. Evidence label: "
            f"{result.label.value.replace('_', ' ')}."
        )
    parts = []
    for section in result.sections:
        default = next(v for v in section.conditions if v.condition == ConditionName.DEFAULT)
        for value in section.conditions:
            if value.condition == ConditionName.DEFAULT:
                continue
            retention = "n/a" if value.retention is None else f"{value.retention:.0%}"
            parts.append(
                f"{section.section_id}, {value.condition.value}: keeps {value.molecules} of {default.molecules} {gene} "
                f"molecules in the {section.cells_labelled} cells labelled {result.population.cell_type} (retention {retention}, "
                f"observed {_pct(value.observed_value)}, home-matched expectation {_pct(value.expectation_home_matched)})"
            )
    return "; ".join(parts) + f". Evidence label: {result.label.value.replace('_', ' ')}."


AUDIT_POPULATION = Tool(
    name="audit_population",
    version="2",
    description=(
        "Audit one measure of one cell population across assignment conditions, per section and pooled over eligible "
        "sections: a gene's presence, a gene set's presence, or the co-expression score over the frozen exclusive "
        "marker pairs. Reports molecules kept, retention, nuclear-overlap share, both random-thinning expectations, "
        "neighbour-proximity shares, ranked evidence regions and the evidence label. Optionally scoped to an ROI box."
    ),
    arguments=AuditPopulationArguments,
    run=_run_audit_population,
    summarize=_summarize_audit_result,
)


def _run_random_thinning_control(arguments: AuditPopulationArguments, context: ToolContext) -> RandomThinningControl:
    return random_thinning_control(_audit(arguments, context))


def _summarize_control(control: RandomThinningControl) -> str:
    below = ", ".join(c.value for c in control.conditions_below_threshold) or "no condition"
    return (
        f"Random-thinning control for {control.finding_id}: {_summarize_pooled(control.pooled)}. Below the threshold "
        f"({control.threshold}): {below}. Evidence label: {control.label.value.replace('_', ' ')}."
    )


RUN_RANDOM_THINNING_CONTROL = Tool(
    name="run_random_thinning_control",
    version="1",
    description=(
        "The required control for a claim about assignment sensitivity: compares an audit's observed values with what "
        "random molecule loss at a matched rate would give, cell-matched (each cell's own retention) and home-matched "
        "(the gene's retention in its home cell type), with the excess drop against each and the frozen verdict."
    ),
    arguments=AuditPopulationArguments,
    run=_run_random_thinning_control,
    summarize=_summarize_control,
)


class LabelSensitivityArguments(AuditPopulationArguments):
    label_rule_ids: list[str] = Field(
        default_factory=lambda: [NPHS1_ANCHORED_RULE, FULL_PANEL_RULE],
        min_length=2,
        max_length=2,
        description="The two frozen label rules to compare; one should not use the finding's genes.",
    )

    @model_validator(mode="after")
    def _presence_only(self) -> "LabelSensitivityArguments":
        if self.measure == "co_expression_score":
            raise ValueError("the label-sensitivity check compares a presence measure")
        return self


def _run_label_sensitivity_check(arguments: LabelSensitivityArguments, context: ToolContext) -> LabelSensitivityCheck:
    by_rule, groups, left_out = {}, {}, {}
    for rule in arguments.label_rule_ids:
        by_rule[rule], groups, left_out = _sections(context, arguments.section_ids, rule, arguments.roi)
    return label_sensitivity_check(
        by_rule, arguments.cell_type, arguments.genes, arguments.conditions,
        section_groups=groups, sections_left_out=left_out, roi=arguments.roi,
    )


def _summarize_label_check(check: LabelSensitivityCheck) -> str:
    return check.summary


RUN_LABEL_SENSITIVITY_CHECK = Tool(
    name="run_label_sensitivity_check",
    version="1",
    description=(
        "The required control for a claim about a population whose label rule involves the claim's genes: the same "
        "measure under two frozen label rules (by default NPHS1-anchored, which ignores LRP2 and CUBN, and full-panel), "
        "with cell counts under each, cells the rules disagree on, and each rule's evidence label."
    ),
    arguments=LabelSensitivityArguments,
    run=_run_label_sensitivity_check,
    summarize=_summarize_label_check,
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


DEFAULT_REGISTRY = ToolRegistry([AUDIT_POPULATION, RUN_RANDOM_THINNING_CONTROL, RUN_LABEL_SENSITIVITY_CHECK])
