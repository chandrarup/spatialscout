"""Audit a population: how a measure of one cell population behaves across assignment conditions.

The population is fixed under the default condition: every condition is computed over the same cells, and a
cell with no retained molecules stays in the denominator. Ticket 01 computes a single gene's presence
(`share_expressing`); ticket 05 adds gene sets, co-expression, both random-thinning expectations, the
neighbour-proximity shares, evidence regions and the full audit label rules.
"""

from collections.abc import Sequence

import numpy as np

from ..contracts import (
    AuditConditionValue,
    AuditResult,
    AuditSectionValues,
    ConditionName,
    EvidenceStatus,
    Population,
    content_id,
)
from ..data import SectionTables
from .conditions import inclusion_mask

POPULATION_GATE_MIN_CELLS = 20

_NOT_COMPUTED_YET = {
    "expectation_cell_matched": "the random-thinning control is not computed yet (ticket 05)",
    "expectation_home_matched": "the random-thinning control is not computed yet (ticket 05)",
    "excess_drop_cell_matched": "needs the cell-matched random-thinning expectation (ticket 05)",
    "excess_drop_home_matched": "needs the home-matched random-thinning expectation (ticket 05)",
    "neighbour_proximity_share_excluded": "the neighbour-proximity share is not computed yet (ticket 05)",
    "neighbour_proximity_share_retained": "the neighbour-proximity share is not computed yet (ticket 05)",
}


def audit_population(
    sections: Sequence[SectionTables],
    cell_type: str,
    genes: Sequence[str],
    conditions: Sequence[ConditionName],
) -> AuditResult:
    """Audit one gene's presence in one cell population, per section and assignment condition."""
    if len(genes) != 1:
        raise ValueError("ticket 01 audits one gene; gene sets and co-expression arrive with ticket 05")
    if len({(s.dataset_id, s.label_rule_id) for s in sections}) != 1:
        raise ValueError("an audit result covers sections of one dataset under one label rule")
    gene = genes[0]
    values = [_section_values(section, cell_type, gene, conditions) for section in sections]
    label, reason = _label(values, cell_type)
    result = AuditResult(
        finding_id="pending",
        dataset_id=sections[0].dataset_id,
        population=Population(label_rule_id=sections[0].label_rule_id, cell_type=cell_type),
        genes=[gene],
        measure="share_expressing",
        sections=values,
        label=label,
        label_reason=reason,
    )
    return result.model_copy(update={"finding_id": content_id("fnd", result.model_dump(mode="json", exclude={"finding_id"}))})


def _section_values(section: SectionTables, cell_type: str, gene: str, conditions: Sequence[ConditionName]) -> AuditSectionValues:
    cells, molecules = section.cells, section.molecules
    population = set(cells.loc[cells["cell_type"] == cell_type, "cell_id"].astype(str))
    in_scope = (
        molecules["cell_id"].isin(population).fillna(False).to_numpy(dtype=bool)
        & (molecules["gene"] == gene).fillna(False).to_numpy(dtype=bool)
        & inclusion_mask(section, ConditionName.DEFAULT)
    )
    nuclear = molecules["overlaps_nucleus"].to_numpy(dtype=bool)
    cell_ids = molecules["cell_id"].astype(str).to_numpy(dtype=object)
    n_default = int(in_scope.sum())
    rows = []
    for condition in conditions:
        kept = in_scope & inclusion_mask(section, condition)
        rows.append(_condition_value(condition, kept, n_default, len(population), nuclear, cell_ids))
    return AuditSectionValues(section_id=section.section_id, cells_labelled=len(population), conditions=rows)


def _condition_value(
    condition: ConditionName, kept: np.ndarray, n_default: int, n_cells: int, nuclear: np.ndarray, cell_ids: np.ndarray
) -> AuditConditionValue:
    n_kept = int(kept.sum())
    expressing = len(set(cell_ids[kept]))
    reasons = dict(_NOT_COMPUTED_YET)
    if not n_default:
        reasons["retention"] = "no molecules of the gene in the population under the default condition"
    if not n_cells:
        reasons["observed_value"] = "no cells carry this label in the section"
    if not n_kept:
        reasons["nuclear_overlap_share"] = "no molecules kept under this condition"
    return AuditConditionValue(
        condition=condition,
        molecules=n_kept,
        retention=n_kept / n_default if n_default else None,
        observed_value=expressing / n_cells if n_cells else None,
        nuclear_overlap_share=int((kept & nuclear).sum()) / n_kept if n_kept else None,
        cells_with_retained_molecule=expressing,
        missing_reasons=reasons,
    )


def _label(values: list[AuditSectionValues], cell_type: str) -> tuple[EvidenceStatus, str]:
    small = [v for v in values if v.cells_labelled < POPULATION_GATE_MIN_CELLS]
    if small:
        counts = ", ".join(f"{v.cells_labelled} in {v.section_id}" for v in small)
        return EvidenceStatus.INSUFFICIENT_EVIDENCE, (
            f"Population gate: cells labelled {cell_type}: {counts}; every section needs at least {POPULATION_GATE_MIN_CELLS}."
        )
    return EvidenceStatus.INSUFFICIENT_EVIDENCE, "Audit labels need the random-thinning expectations, which ticket 05 adds."
