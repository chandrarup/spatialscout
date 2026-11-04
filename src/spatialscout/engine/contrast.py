"""Descriptive disease contrasts: one gene in one cell population, a disease group against the control group.

Follows the spec's frozen analysis rules literally (ADR-0007: descriptive only, no p-values or intervals):

- **Fixed populations.** Cells carry their default-condition label; every condition is computed over the same cells.
- **Normalisation.** Per section and condition, the library size is the population's pseudobulk total (molecules of
  every gene kept under the condition in population cells). Value: log2(CP10K + 1) of the gene.
- **Effect.** The disease group's mean value minus the control group's (a log2 ratio of geometric means of CP10K + 1).
- **Gate precedence.** (1) every section of both groups passes the population gate (20 cells), else insufficient
  evidence; (2) a condition is valid only if every section has at least 10 of the gene's molecules in the
  population under it; (3) default plus at least one stricter primary condition must be valid, else insufficient.
- **Labels.** Direction is 0 within ±0.1 log2. Stable: two or more valid primary conditions, no reversal (two valid
  conditions with opposite non-zero directions), effect range at most 0.5, and no leave-one-section-out flip (an
  opposite non-zero direction) in any valid condition. Segmentation-sensitive: a reversal or a range above 0.5,
  with no leave-one-section-out flip under the default condition. Otherwise insufficient evidence.
- **Exploratory condition.** Structure-constrained values are computed apart, on sections with structure masks
  only, and never reach a label (ADR-0006).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from ..contracts import (
    ConditionEffect,
    ConditionName,
    Contrast,
    ContrastResult,
    ContrastRules,
    ContrastSection,
    EvidenceStatus,
    LeaveOneSectionOut,
    LeftOutSection,
    Population,
    SectionLog2Value,
    content_id,
)
from ..data import SectionTables
from .conditions import EXPLORATORY_CONDITIONS, PRIMARY_CONDITIONS
from .population import MOLECULE_GATE_MIN_MOLECULES, POPULATION_GATE_MIN_CELLS, _evidence_regions, _index, ranking_rule

NEAR_ZERO_BAND = 0.1
MAX_STABLE_RANGE = 0.5
CP10K = 1e4

NORMALISATION = "Library size: the pseudobulk total of the population (molecules of every gene in its cells) in that section under that condition."
VALUE_RULE = "log2(CP10K + 1), with CP10K = 10,000 x the gene's molecules in the population / the library size."
EFFECT_RULE = "Mean of the disease group's per-section log2 values minus the mean of the control group's, per condition."
GATE_PRECEDENCE = (
    f"1. Every section of both groups must have at least {POPULATION_GATE_MIN_CELLS} cells of the population, else "
    f"insufficient evidence. 2. A condition is valid only if every section has at least {MOLECULE_GATE_MIN_MOLECULES} "
    "of the gene's molecules in the population under it. 3. The default condition and at least one stricter primary "
    "condition must be valid, else insufficient evidence."
)
LABEL_RULE = (
    f"A direction within ±{NEAR_ZERO_BAND} log2 is none. A reversal is two valid conditions with opposite non-zero "
    f"directions. Stable: at least two valid primary conditions, no reversal, an effect range of at most {MAX_STABLE_RANGE} "
    "log2, and leaving out any one section never gives an opposite non-zero direction in any valid condition. "
    f"Segmentation-sensitive: a reversal or a range above {MAX_STABLE_RANGE}, with the default effect's direction kept "
    "whichever section is left out. Otherwise insufficient evidence. The exploratory condition never enters the label."
)


def contrast_rules(label_rule_id: str) -> ContrastRules:
    return ContrastRules(
        population_gate_min_cells=POPULATION_GATE_MIN_CELLS,
        molecule_gate_min_molecules=MOLECULE_GATE_MIN_MOLECULES,
        near_zero_band_log2=NEAR_ZERO_BAND,
        max_stable_range_log2=MAX_STABLE_RANGE,
        label_rule_id=label_rule_id,
        normalisation=NORMALISATION,
        value_rule=VALUE_RULE,
        effect_rule=EFFECT_RULE,
        gate_precedence=GATE_PRECEDENCE,
        label_rule=LABEL_RULE,
        primary_conditions=list(PRIMARY_CONDITIONS),
        exploratory_conditions=list(EXPLORATORY_CONDITIONS),
    )


def direction(effect: float | None) -> int | None:
    if effect is None:
        return None
    return 0 if abs(effect) <= NEAR_ZERO_BAND else (1 if effect > 0 else -1)


@dataclass
class _Scope:
    """The gene's default molecules in the population of one section, for ranking evidence windows."""

    section_id: str
    scope_x: np.ndarray
    scope_y: np.ndarray
    kept: dict[ConditionName, np.ndarray]

    @property
    def values(self):  # the shape `_evidence_regions` reads
        return self


def _section_values(section: SectionTables, group: str, cell_type: str, gene: str, conditions: Sequence[ConditionName]):
    index = _index(section)
    in_population = index.type_codes == index.type_code(cell_type)
    n_cells = int(in_population.sum())
    assigned = index.cell_codes >= 0
    population_molecule = np.zeros(len(index.cell_codes), dtype=bool)
    population_molecule[assigned] = in_population[index.cell_codes[assigned]]
    of_gene = population_molecule & (index.gene_codes == index.gene_code(gene)) if index.gene_code(gene) >= 0 else np.zeros_like(population_molecule)
    values = []
    for condition in conditions:
        library = int(index.per_cell(condition)[in_population].sum())
        count = int((of_gene & index.mask(condition)).sum())
        value, reason = None, None
        if library:
            value = float(np.log2(CP10K * count / library + 1.0))
        else:
            reason = f"no molecules in {cell_type} cells under {condition.value}"
        values.append(SectionLog2Value(
            section_id=section.section_id, group=group, condition=condition, library_size=library, log2_value=value,
            missing_reason=reason, gene_molecules=count, passes_molecule_gate=count >= MOLECULE_GATE_MIN_MOLECULES,
        ))
    default_rows = np.flatnonzero(of_gene & index.mask(ConditionName.DEFAULT))
    scope = _Scope(section.section_id, index.x[default_rows], index.y[default_rows],
                   {c: index.mask(c)[default_rows] for c in conditions})
    return n_cells, values, scope


def _effect(values: Sequence[SectionLog2Value], contrast: Contrast, condition: ConditionName, left_out: str | None = None):
    rows = [v for v in values if v.condition == condition and v.section_id != left_out]
    disease = [v.log2_value for v in rows if v.group == contrast.disease]
    control = [v.log2_value for v in rows if v.group == contrast.control]
    if not disease or not control or any(x is None for x in disease + control):
        return None, None, None, [v.section_id for v in rows]
    d, c = float(np.mean(disease)), float(np.mean(control))
    return d - c, d, c, [v.section_id for v in rows]


def compute_contrast(
    sections: Sequence[SectionTables],
    section_groups: Mapping[str, str],
    contrast: Contrast,
    cell_type: str,
    gene: str,
    conditions: Sequence[ConditionName] = PRIMARY_CONDITIONS,
    *,
    inference_reason: str,
    donor_distinctness: str | None = None,
    sections_left_out: Mapping[str, str] | None = None,
    section_disclosure: str | None = None,
) -> ContrastResult:
    """One gene in one cell population, the disease group against the control group, under every condition, with
    per-section values, leave-one-section-out influence and the frozen contrast label. Sections whose group is
    neither side of the contrast are ignored."""
    if ConditionName.DEFAULT not in conditions:
        raise ValueError("the default condition is required: populations are fixed under it")
    sections = [s for s in sections if section_groups.get(s.section_id) in (contrast.disease, contrast.control)]
    if len({(s.dataset_id, s.label_rule_id) for s in sections}) != 1:
        raise ValueError("a contrast result covers sections of one dataset under one label rule")
    exploratory = [c for c in conditions if c in EXPLORATORY_CONDITIONS]
    primary = [ConditionName.DEFAULT] + [c for c in conditions if c in PRIMARY_CONDITIONS and c != ConditionName.DEFAULT]

    summaries, per_section, scopes, exploratory_values = [], [], [], []
    for s in sections:
        group = section_groups[s.section_id]
        n_cells, values, scope = _section_values(s, group, cell_type, gene, primary)
        summaries.append(ContrastSection(section_id=s.section_id, group=group, cells_labelled=n_cells,
                                         passes_population_gate=n_cells >= POPULATION_GATE_MIN_CELLS))
        per_section += values
        scopes.append(scope)
        if exploratory and s.structures:
            exploratory_values += _section_values(s, group, cell_type, gene, exploratory)[1]

    effects = []
    for condition in primary:
        effect, d, c, used = _effect(per_section, contrast, condition)
        failing = [v.section_id for v in per_section if v.condition == condition and not v.passes_molecule_gate]
        effects.append(ConditionEffect(
            condition=condition, effect=effect, disease_mean=d, control_mean=c, direction=direction(effect),
            missing_reason=None if effect is not None else "a group has no section, or a section has no value",
            valid=not failing and effect is not None,
            invalid_reason=(f"below the molecule gate ({MOLECULE_GATE_MIN_MOLECULES} {gene} molecules) in {', '.join(failing)}" if failing
                            else None if effect is not None else "no effect"),
            sections_used=used,
        ))
    exploratory_effects = []
    for condition in exploratory:
        effect, d, c, used = _effect(exploratory_values, contrast, condition)
        exploratory_effects.append(ConditionEffect(
            condition=condition, effect=effect, disease_mean=d, control_mean=c, direction=direction(effect), sections_used=used,
            missing_reason=None if effect is not None else
            "needs structure masks on at least one section of each group; computed on the sections that have them",
        ))

    valid = [e.condition for e in effects if e.valid]
    loo = []
    for section in summaries:
        for e in effects:
            if e.condition not in valid:
                continue
            left, *_ = _effect(per_section, contrast, e.condition, left_out=section.section_id)
            d = direction(left)
            loo.append(LeaveOneSectionOut(
                left_out_section_id=section.section_id, condition=e.condition, effect=left, direction=d,
                direction_kept=None if left is None else not (e.direction and d and d == -e.direction),
            ))
    label, reason = _label(summaries, effects, valid, loo, cell_type)

    region_condition = next((c for c in (ConditionName.NUCLEUS_ONLY, ConditionName.DISTANCE_CAP_1UM, ConditionName.DISTANCE_CAP_2UM) if c in primary), None)
    result = ContrastResult(
        finding_id="pending",
        dataset_id=sections[0].dataset_id,
        groups=contrast,
        population=Population(label_rule_id=sections[0].label_rule_id, cell_type=cell_type),
        gene=gene,
        per_section=per_section,
        effects=effects,
        leave_one_section_out=loo,
        exploratory_effects=exploratory_effects,
        inference_reason=inference_reason,
        label=label,
        label_reason=reason,
        donor_distinctness=donor_distinctness,
        sections=summaries,
        sections_left_out=[LeftOutSection(section_id=k, reason=v) for k, v in sorted((sections_left_out or {}).items())],
        valid_conditions=valid,
        exploratory_per_section=exploratory_values,
        evidence_regions=_evidence_regions(scopes, region_condition) if region_condition else [],
        ranking_rule=ranking_rule(region_condition).replace("Eligible sections only (every section when none is eligible)", "Every section of both groups") if region_condition else None,
        rules=contrast_rules(sections[0].label_rule_id),
        section_disclosure=section_disclosure,
    )
    return result.model_copy(update={"finding_id": content_id("fnd", result.model_dump(mode="json", exclude={"finding_id"}))})


def _label(sections, effects, valid, loo, cell_type) -> tuple[EvidenceStatus, str]:
    insufficient = EvidenceStatus.INSUFFICIENT_EVIDENCE
    failing = [s.section_id for s in sections if not s.passes_population_gate]
    if failing:
        return insufficient, (
            f"{', '.join(failing)} {'has' if len(failing) == 1 else 'have'} fewer than {POPULATION_GATE_MIN_CELLS} cells "
            f"labelled {cell_type}, so the population gate fails."
        )
    if ConditionName.DEFAULT not in valid or len(valid) < 2:
        return insufficient, (
            f"{len(valid)} valid primary condition{'s' if len(valid) != 1 else ''} ({', '.join(c.value for c in valid) or 'none'}); "
            "the default condition and at least one stricter one must pass the molecule gate in every section."
        )
    by = {e.condition: e for e in effects if e.condition in valid}
    directions = {e.direction for e in by.values()}
    reversal = 1 in directions and -1 in directions
    values = [e.effect for e in by.values()]
    spread = max(values) - min(values)
    flips = sorted({(f.left_out_section_id, f.condition.value) for f in loo if f.direction_kept is False})
    unknown = any(f.direction_kept is None for f in loo)
    default_flips = [s for s, c in flips if c == ConditionName.DEFAULT.value]
    if not reversal and spread <= MAX_STABLE_RANGE and not flips and not unknown:
        return EvidenceStatus.STABLE, (
            f"Across {len(valid)} valid primary conditions the effect keeps its direction (range {spread:.2f} log2, at most "
            f"{MAX_STABLE_RANGE}), and leaving out any one section never reverses it."
        )
    if (reversal or spread > MAX_STABLE_RANGE) and not default_flips and not unknown:
        what = "the direction reverses between valid conditions" if reversal else f"the effect range is {spread:.2f} log2, above {MAX_STABLE_RANGE}"
        return EvidenceStatus.SEGMENTATION_SENSITIVE, (
            f"Across {len(valid)} valid primary conditions {what}, and the default effect keeps its direction whichever section is left out."
        )
    if flips:
        shown = ", ".join(f"{s} ({c})" for s, c in flips[:4]) + (" …" if len(flips) > 4 else "")
        return insufficient, f"Leaving out one section reverses the effect's direction: {shown}."
    return insufficient, "A leave-one-section-out effect could not be computed."


__all__ = ["compute_contrast", "contrast_rules", "direction"]
