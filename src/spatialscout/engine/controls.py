"""The two required controls a claim cites: the random-thinning control and the label-sensitivity check."""

from collections.abc import Mapping, Sequence

from ..contracts import (
    AuditResult,
    ConditionName,
    EvidenceStatus,
    LabelRuleArm,
    LabelSensitivityCheck,
    RandomThinningControl,
    Region,
    content_id,
)
from ..data import SectionTables
from .conditions import PRIMARY_CONDITIONS
from .population import EXCESS_LOG2_DROP, audit_population, restrict_to_roi


def random_thinning_control(result: AuditResult) -> RandomThinningControl:
    """An audit result's observed values against both random-thinning expectations, with the verdict per stricter
    condition under the frozen audit threshold."""
    control = RandomThinningControl(
        control_id="pending",
        finding_id=result.finding_id,
        dataset_id=result.dataset_id,
        label_rule_id=result.population.label_rule_id,
        cell_type=result.population.cell_type,
        genes=result.genes,
        measure=result.measure,
        eligible_section_ids=result.eligible_section_ids,
        pooled=result.pooled,
        sections=result.sections,
        threshold=f"observed below the home-matched expectation x 2^-{EXCESS_LOG2_DROP} (an excess log2 drop above {EXCESS_LOG2_DROP})",
        conditions_below_threshold=[p.condition for p in result.pooled if p.below_home_threshold],
        label=result.label,
        label_reason=result.label_reason,
        roi=result.roi,
    )
    return control.model_copy(update={"control_id": content_id("ctl", control.model_dump(mode="json", exclude={"control_id"}))})


def label_sensitivity_check(
    sections_by_rule: Mapping[str, Sequence[SectionTables]],
    cell_type: str,
    genes: Sequence[str],
    conditions: Sequence[ConditionName] = PRIMARY_CONDITIONS,
    *,
    section_groups: Mapping[str, str] | None = None,
    sections_left_out: Mapping[str, str] | None = None,
    roi: Region | None = None,
) -> LabelSensitivityCheck:
    """The same measure of the same population under two label rules (the same sections, labelled twice), with the
    cells each rule puts in the population and how many cells the rules disagree on."""
    if len(sections_by_rule) != 2:
        raise ValueError("a label-sensitivity check compares exactly two label rules")
    (first_rule, first), (second_rule, second) = sections_by_rule.items()
    arms = []
    for rule, sections in ((first_rule, first), (second_rule, second)):
        result = audit_population(
            sections, cell_type, genes, conditions, section_groups=section_groups, sections_left_out=sections_left_out, roi=roi
        )
        arms.append(
            LabelRuleArm(
                label_rule_id=rule,
                finding_id=result.finding_id,
                cells_labelled=sum(s.cells_labelled for s in result.sections),
                cells_labelled_by_section={s.section_id: s.cells_labelled for s in result.sections},
                eligible_section_ids=result.eligible_section_ids,
                pooled=result.pooled,
                label=result.label,
                label_reason=result.label_reason,
            )
        )
    both = only_first = only_second = 0
    second_by_id = {s.section_id: s for s in second}
    for section in first:
        a = _population_ids(restrict_to_roi(section, roi) if roi else section, cell_type)
        other = second_by_id[section.section_id]
        b = _population_ids(restrict_to_roi(other, roi) if roi else other, cell_type)
        both, only_first, only_second = both + len(a & b), only_first + len(a - b), only_second + len(b - a)
    same = arms[0].label == arms[1].label
    summary = (
        f"{cell_type} under {first_rule}: {arms[0].cells_labelled} cells, {_label_text(arms[0].label)}; under {second_rule}: "
        f"{arms[1].cells_labelled} cells, {_label_text(arms[1].label)}. {both} cells are in both populations, {only_first} "
        f"only under {first_rule}, {only_second} only under {second_rule}."
    )
    check = LabelSensitivityCheck(
        control_id="pending",
        dataset_id=first[0].dataset_id,
        cell_type=cell_type,
        genes=list(genes),
        measure="share_expressing" if len(genes) == 1 else "gene_set_share_expressing",
        arms=arms,
        cells_in_both=both,
        cells_only_first=only_first,
        cells_only_second=only_second,
        same_label=same,
        summary=summary,
        roi=roi,
    )
    return check.model_copy(update={"control_id": content_id("ctl", check.model_dump(mode="json", exclude={"control_id"}))})


def _population_ids(section: SectionTables, cell_type: str) -> set[str]:
    cells = section.cells
    return set(cells.loc[cells["cell_type"] == cell_type, "cell_id"].astype(str))


def _label_text(label: EvidenceStatus) -> str:
    return label.value.replace("_", " ")
