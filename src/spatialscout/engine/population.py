"""Audit a population: how a measure of one cell population behaves across assignment conditions.

Follows the spec's frozen analysis rules literally:

- **Fixed populations.** Cells are labelled once under the default condition; every condition is computed over
  the same cells, and a cell with no retained molecules stays in the denominator.
- **Measures.** A gene's presence (`share_expressing`), a gene set's presence (`gene_set_share_expressing`, any
  of the genes), or the co-expression score over exclusive marker pairs: per pair, cells expressing both over
  cells expressing either, averaged over the pairs any population cell expresses under the default condition.
- **Random-thinning expectations (closed form).** For cell c with k default molecules of gene g, the chance g
  survives is p = 1 - (1 - r)^k, with r the cell's own retention (cell-matched) or g's retention in its home
  cell type in that section under the condition (home-matched). Share expressing: mean p; gene set:
  1 - prod(1 - p_g); pair: sum p_g p_h / sum (p_g + p_h - p_g p_h). Excess drop: expectation minus observed.
- **Gates.** A section is eligible with at least 20 population cells and 10 of the result's molecules in them
  under the default condition; at least 3 eligible sections are needed. Stricter conditions are not gated.
- **Label.** Pooled over eligible sections (ratio of sums), under each stricter primary condition:
  segmentation-sensitive when one condition has O < E_home x 2^-0.5 in the full pool and with any one eligible
  section left out; stable when no condition does, in the full pool and every leave-one-out; otherwise
  insufficient evidence, as is a gene with no home cell type.

Everything is vectorised over integer codes, so a section of millions of molecules audits in seconds.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from ..contracts import (
    AuditConditionValue,
    AuditResult,
    AuditRules,
    AuditSectionValues,
    ConditionName,
    EvidenceRegion,
    EvidenceStatus,
    GateStatus,
    LeaveOneSectionOutVerdict,
    LeftOutSection,
    PooledConditionValue,
    Population,
    Region,
    content_id,
)
from ..data import SectionTables, make_section
from .conditions import PRIMARY_CONDITIONS, inclusion_mask
from .markers import HOME_CELL_TYPES, MarkerPairs, load_marker_pairs

POPULATION_GATE_MIN_CELLS = 20
MOLECULE_GATE_MIN_MOLECULES = 10
MIN_ELIGIBLE_SECTIONS = 3
EXCESS_LOG2_DROP = 0.5
THRESHOLD_FACTOR = 2.0**-EXCESS_LOG2_DROP
WINDOW_UM = 150.0
TOP_REGIONS = 10

Measure = Literal["share_expressing", "gene_set_share_expressing", "co_expression_score"]

POOLING_RULE = (
    "Ratio of sums over the eligible sections: observed = cells meeting the measure / cells of the population, "
    "expectation = sum of per-cell survival probabilities / cells; for the co-expression score, per pair the "
    "summed 'both' over the summed 'either' (and the same for the expectation's terms), averaged over the pairs "
    "any pooled population cell expresses under the default condition."
)
LABEL_RULE = (
    "Under each stricter primary condition, compare the pooled observed value O with the pooled home-matched "
    "expectation E. Segmentation-sensitive: one condition has O < E x 2^-0.5 in the full pool and with each "
    "eligible section left out. Stable: no condition does, in the full pool or any leave-one-out. Otherwise, "
    "fewer than 3 eligible sections, or a gene with no home cell type: insufficient evidence."
)
EXPECTATION_RULE = (
    "Closed form. Cell-matched p = 1 - (1 - r_c)^k with r_c the cell's retention over all its genes; home-matched "
    "p = 1 - (1 - rho)^k with rho the gene's retention in its home cell type, in that section, under the condition. "
    "Share: mean p; gene set: mean of 1 - prod(1 - p_g); pair: sum p_g p_h / sum (p_g + p_h - p_g p_h)."
)


def result_molecules_rule(measure: Measure) -> str:
    if measure == "co_expression_score":
        return (
            "Molecules of the scored pairs' genes whose home cell type is not the population, assigned to population "
            "cells under the default condition (the foreign markers an admixture would bring in)."
        )
    return "Molecules of the result's genes assigned to population cells under the default condition."


def ranking_rule(condition: ConditionName) -> str:
    return (
        f"150 x 150 µm windows on a grid anchored at (0, 0) in section coordinates, ranked by the result's molecules "
        f"in the population excluded under {condition.value}; ties go to more default-condition molecules in the "
        f"window, then section id, y0 and x0. Eligible sections only (every section when none is eligible); the top "
        f"{TOP_REGIONS} windows with at least one excluded molecule are kept."
    )


# --- per-section indexing, cached ------------------------------------------------------------------------------


@dataclass
class _Index:
    """Integer codes for one section, computed once: each molecule's cell and gene, and the condition masks."""

    section: SectionTables
    cell_codes: np.ndarray
    cell_types: list[str]
    type_codes: np.ndarray
    genes: list[str]
    gene_codes: np.ndarray
    cell_x: np.ndarray
    cell_y: np.ndarray
    x: np.ndarray
    y: np.ndarray
    nuclear: np.ndarray
    masks: dict[ConditionName, np.ndarray] = field(default_factory=dict)
    _per_cell: dict[ConditionName, np.ndarray] = field(default_factory=dict)

    def mask(self, condition: ConditionName) -> np.ndarray:
        if condition not in self.masks:
            self.masks[condition] = inclusion_mask(self.section, condition) & (self.cell_codes >= 0)
        return self.masks[condition]

    def per_cell(self, condition: ConditionName) -> np.ndarray:
        """Molecules of every gene counted toward each cell under the condition."""
        if condition not in self._per_cell:
            codes = self.cell_codes[self.mask(condition)]
            self._per_cell[condition] = np.bincount(codes, minlength=len(self.cell_x))
        return self._per_cell[condition]

    def gene_code(self, gene: str) -> int:
        return self.genes.index(gene) if gene in self.genes else -1

    def type_code(self, cell_type: str) -> int:
        return self.cell_types.index(cell_type) if cell_type in self.cell_types else -1


_INDEXES: dict[int, _Index] = {}


def _index(section: SectionTables) -> _Index:
    cached = _INDEXES.get(id(section))
    if cached is not None and cached.section is section:
        return cached
    molecules, cells = section.molecules, section.cells
    cell_ids = pd.Index(cells["cell_id"].astype(str))
    cell_codes = cell_ids.get_indexer(molecules["cell_id"].astype("string").fillna("\0unassigned").astype(str))
    gene_cat = pd.Categorical(molecules["gene"].astype(str))
    type_cat = pd.Categorical(cells["cell_type"].astype(str))
    index = _Index(
        section=section,
        cell_codes=cell_codes.astype(np.int64),
        cell_types=[str(t) for t in type_cat.categories],
        type_codes=type_cat.codes.astype(np.int64),
        genes=[str(g) for g in gene_cat.categories],
        gene_codes=gene_cat.codes.astype(np.int64),
        cell_x=cells["x"].to_numpy(dtype=float),
        cell_y=cells["y"].to_numpy(dtype=float),
        x=molecules["x"].to_numpy(dtype=float),
        y=molecules["y"].to_numpy(dtype=float),
        nuclear=molecules["overlaps_nucleus"].to_numpy(dtype=bool),
    )
    if len(_INDEXES) > 64:
        _INDEXES.clear()
    _INDEXES[id(section)] = index
    return index


# --- ROI -------------------------------------------------------------------------------------------------------


def _cells_in(index: _Index, roi: Region) -> np.ndarray:
    return (index.cell_x >= roi.x0) & (index.cell_x <= roi.x1) & (index.cell_y >= roi.y0) & (index.cell_y <= roi.y1)


def restrict_to_roi(section: SectionTables, roi: Region) -> SectionTables:
    """The section cut to a box: cells whose centroid lies inside, with all their molecules."""
    if roi.section_id != section.section_id:
        raise ValueError(f"the ROI is on section {roi.section_id}, not {section.section_id}")
    index = _index(section)
    inside = _cells_in(index, roi)
    keep = (index.cell_codes >= 0) & inside[np.clip(index.cell_codes, 0, None)]
    return make_section(
        section.section_id,
        section.dataset_id,
        section.label_rule_id,
        molecules=section.molecules[keep],
        cells=section.cells[inside],
    )


def gate_status(section: SectionTables, roi: Region | None, cell_type: str, genes: Sequence[str]) -> GateStatus:
    """Population cells and their default molecules of `genes` inside a box, against the frozen gates."""
    index = _index(section)
    in_population = index.type_codes == index.type_code(cell_type)
    if roi is not None:
        if roi.section_id != section.section_id:
            raise ValueError(f"the ROI is on section {roi.section_id}, not {section.section_id}")
        in_population &= _cells_in(index, roi)
    codes = [c for c in (index.gene_code(g) for g in genes) if c >= 0]
    assigned = index.cell_codes >= 0
    hit = assigned & np.isin(index.gene_codes, codes)
    hit[hit] = in_population[index.cell_codes[hit]]
    cells, molecules = int(in_population.sum()), int(hit.sum())
    passes_cells, passes_molecules = cells >= POPULATION_GATE_MIN_CELLS, molecules >= MOLECULE_GATE_MIN_MOLECULES
    gene_text = " or ".join(genes)
    status = f"{cells} {cell_type} cells · {molecules} {gene_text} molecules · " + (
        "passes both gates" if passes_cells and passes_molecules
        else "below population gate" if not passes_cells
        else "below molecule gate"
    )
    return GateStatus(
        section_id=section.section_id,
        roi=roi,
        cell_type=cell_type,
        genes=list(genes),
        cells=cells,
        molecules=molecules,
        population_gate_min_cells=POPULATION_GATE_MIN_CELLS,
        molecule_gate_min_molecules=MOLECULE_GATE_MIN_MOLECULES,
        passes_population_gate=passes_cells,
        passes_molecule_gate=passes_molecules,
        status=status,
    )


# --- one section ------------------------------------------------------------------------------------------------


@dataclass
class _Terms:
    """Numerators and denominators of one section under one condition, kept for pooling. Presence measures hold
    one entry; the co-expression score holds one per pair."""

    observed_num: np.ndarray
    observed_den: np.ndarray
    cell_num: np.ndarray
    cell_den: np.ndarray
    home_num: np.ndarray | None
    home_den: np.ndarray | None
    molecules: int
    default_molecules: int


@dataclass
class _SectionAudit:
    values: AuditSectionValues
    terms: dict[ConditionName, _Terms]
    eligible: bool
    scope_x: np.ndarray
    scope_y: np.ndarray
    kept: dict[ConditionName, np.ndarray]


def _survival(retention: np.ndarray, k: np.ndarray) -> np.ndarray:
    return 1.0 - np.power(1.0 - np.clip(retention, 0.0, 1.0), k)


def _audit_one(
    section: SectionTables,
    cell_type: str,
    genes: list[str],
    measure: Measure,
    pairs: list[tuple[int, int]],
    conditions: Sequence[ConditionName],
    group: str | None,
) -> _SectionAudit:
    index = _index(section)
    population = np.flatnonzero(index.type_codes == index.type_code(cell_type))
    n_cells = len(population)
    position = np.full(len(index.cell_x), -1, dtype=np.int64)
    position[population] = np.arange(n_cells)
    gene_position = np.full(len(index.genes), -1, dtype=np.int64)
    for i, gene in enumerate(genes):
        code = index.gene_code(gene)
        if code >= 0:
            gene_position[code] = i
    n_genes = len(genes)

    default = index.mask(ConditionName.DEFAULT)
    candidates = np.flatnonzero(default)
    candidates = candidates[(position[index.cell_codes[candidates]] >= 0) & (gene_position[index.gene_codes[candidates]] >= 0)]
    cell_pos = position[index.cell_codes[candidates]]
    gene_pos = gene_position[index.gene_codes[candidates]]
    flat = cell_pos * n_genes + gene_pos
    k = np.bincount(flat, minlength=n_cells * n_genes).reshape(n_cells, n_genes)

    homes = [HOME_CELL_TYPES.get(g) for g in genes]
    foreign = np.array([home != cell_type for home in homes]) if measure == "co_expression_score" else np.ones(n_genes, dtype=bool)
    in_result = foreign[gene_pos]
    n_default = int(in_result.sum())

    # Each scoped molecule: is it closer to a cell of its gene's home type than to its own cell's centroid?
    closer = _closer_to_home(index, candidates[in_result], [homes[g] for g in gene_pos[in_result]])

    # Home-matched retention per gene: kept / default molecules of the gene in its home cell type.
    home_default, home_kept = _home_counts(index, genes, homes, conditions)

    default_per_cell = index.per_cell(ConditionName.DEFAULT)[population]
    rows: list[AuditConditionValue] = []
    terms: dict[ConditionName, _Terms] = {}
    kept_by_condition: dict[ConditionName, np.ndarray] = {}
    supported = None
    for condition in conditions:
        kept_mol = index.mask(condition)[candidates]
        kept_by_condition[condition] = kept_mol[in_result]
        kk = np.bincount(flat[kept_mol], minlength=n_cells * n_genes).reshape(n_cells, n_genes)
        kept_per_cell = index.per_cell(condition)[population]
        r_cell = np.divide(kept_per_cell, default_per_cell, out=np.zeros(n_cells), where=default_per_cell > 0)
        p_cell = _survival(r_cell[:, None], k)
        rho = [home_kept[condition][g] / home_default[g] if home_default[g] else None for g in range(n_genes)]
        reasons: dict[str, str] = {}
        missing_home = [genes[g] for g in range(n_genes) if rho[g] is None and k[:, g].any()]
        if missing_home:
            p_home = None
            reasons["expectation_home_matched"] = (
                f"no default molecules of {', '.join(missing_home)} in its home cell type in this section"
                if all(homes[genes.index(g)] for g in missing_home)
                else f"{', '.join(g for g in missing_home if homes[genes.index(g)] is None)} has no home cell type"
            )
        else:
            p_home = _survival(np.array([r if r is not None else 0.0 for r in rho])[None, :], k)

        if measure == "co_expression_score":
            expressed, kept_expressed = k > 0, kk > 0
            a, b = (np.array([p[0] for p in pairs], dtype=int), np.array([p[1] for p in pairs], dtype=int)) if pairs else (np.zeros(0, int), np.zeros(0, int))
            if supported is None:
                supported = (expressed[:, a] | expressed[:, b]).any(axis=0)
            both = (kept_expressed[:, a] & kept_expressed[:, b]).sum(axis=0).astype(float)
            either = (kept_expressed[:, a] | kept_expressed[:, b]).sum(axis=0).astype(float)
            cell_num = (p_cell[:, a] * p_cell[:, b]).sum(axis=0)
            cell_den = (p_cell[:, a] + p_cell[:, b] - p_cell[:, a] * p_cell[:, b]).sum(axis=0)
            home_num = home_den = None
            if p_home is not None:
                home_num = (p_home[:, a] * p_home[:, b]).sum(axis=0)
                home_den = (p_home[:, a] + p_home[:, b] - p_home[:, a] * p_home[:, b]).sum(axis=0)
            # Pairs no population cell expresses under the default condition are not scored in this section.
            mask = supported.astype(float)
            t = _Terms(both * mask, either * mask, cell_num * mask, cell_den * mask,
                       None if home_num is None else home_num * mask, None if home_den is None else home_den * mask, 0, 0)
            observed = _pair_mean(t.observed_num, t.observed_den, supported)
            e_cell = _pair_mean(t.cell_num, t.cell_den, supported)
            e_home = None if t.home_num is None else _pair_mean(t.home_num, t.home_den, supported)
            cells_expressing = None
            pairs_scored = int(supported.sum())
            if not pairs_scored:
                reasons["observed_value"] = "no population cell expresses either gene of any marker pair under the default condition"
        else:
            expressing = (kk > 0).any(axis=1)
            cells_expressing = int(expressing.sum())
            gene_set = lambda p: 1.0 - np.prod(1.0 - p, axis=1)  # noqa: E731
            t = _Terms(
                np.array([cells_expressing], float), np.array([n_cells], float),
                np.array([gene_set(p_cell).sum()]), np.array([n_cells], float),
                None if p_home is None else np.array([gene_set(p_home).sum()]),
                None if p_home is None else np.array([n_cells], float), 0, 0,
            )
            observed = cells_expressing / n_cells if n_cells else None
            e_cell = float(t.cell_num[0] / n_cells) if n_cells else None
            e_home = float(t.home_num[0] / n_cells) if (n_cells and t.home_num is not None) else None
            pairs_scored = None
            if not n_cells:
                reasons["observed_value"] = "no cells carry this label in the section"

        n_kept = int(kept_mol[in_result].sum())
        t.molecules, t.default_molecules = n_kept, n_default
        terms[condition] = t
        excluded = ~kept_mol[in_result]
        share_excluded = float(closer[excluded].mean()) if excluded.any() else None
        share_retained = float(closer[~excluded].mean()) if (~excluded).any() else None
        if share_excluded is None:
            reasons["neighbour_proximity_share_excluded"] = "no molecules of the result are excluded under this condition"
        if share_retained is None:
            reasons["neighbour_proximity_share_retained"] = "no molecules of the result are kept under this condition"
        if not n_default:
            reasons["retention"] = "no molecules of the result in the population under the default condition"
        if not n_kept:
            reasons["nuclear_overlap_share"] = "no molecules kept under this condition"
        if e_cell is None:
            reasons.setdefault("expectation_cell_matched", "no expectation without population cells")
        if e_home is None:
            reasons.setdefault("expectation_home_matched", "no expectation without population cells")
        rows.append(
            AuditConditionValue(
                condition=condition,
                molecules=n_kept,
                retention=n_kept / n_default if n_default else None,
                observed_value=observed,
                nuclear_overlap_share=float(index.nuclear[candidates[in_result]][kept_mol[in_result]].mean()) if n_kept else None,
                cells_with_retained_molecule=int((kept_per_cell > 0).sum()),
                expectation_cell_matched=e_cell,
                expectation_home_matched=e_home,
                excess_drop_cell_matched=None if (e_cell is None or observed is None) else e_cell - observed,
                excess_drop_home_matched=None if (e_home is None or observed is None) else e_home - observed,
                neighbour_proximity_share_excluded=share_excluded,
                neighbour_proximity_share_retained=share_retained,
                missing_reasons=reasons,
                cells_expressing=cells_expressing,
                pairs_scored=pairs_scored,
            )
        )
        for name in ("excess_drop_cell_matched", "excess_drop_home_matched"):
            if getattr(rows[-1], name) is None:
                reasons.setdefault(name, "needs both the observed value and its expectation")

    eligible_reason = None
    if n_cells < POPULATION_GATE_MIN_CELLS:
        eligible_reason = f"{n_cells} cells labelled {cell_type}; the population gate needs {POPULATION_GATE_MIN_CELLS}"
    elif n_default < MOLECULE_GATE_MIN_MOLECULES:
        eligible_reason = f"{n_default} of the result's molecules under the default condition; the molecule gate needs {MOLECULE_GATE_MIN_MOLECULES}"
    values = AuditSectionValues(
        section_id=section.section_id,
        cells_labelled=n_cells,
        conditions=rows,
        group=group,
        eligible=eligible_reason is None,
        ineligible_reason=eligible_reason,
    )
    scoped = candidates[in_result]
    return _SectionAudit(values, terms, eligible_reason is None, index.x[scoped], index.y[scoped], kept_by_condition)


def _pair_mean(num: np.ndarray, den: np.ndarray, supported: np.ndarray) -> float | None:
    if not supported.any():
        return None
    ratios = np.divide(num, den, out=np.zeros_like(num, dtype=float), where=den > 0)
    return float(ratios[supported].mean())


def _home_counts(index: _Index, genes: list[str], homes: list[str | None], conditions: Sequence[ConditionName]):
    """Per gene, default and per-condition kept molecules of the gene in cells of its home type."""
    n = len(genes)
    default_counts = np.zeros(n, dtype=np.int64)
    kept = {c: np.zeros(n, dtype=np.int64) for c in conditions}
    assigned = index.cell_codes >= 0
    for g, (gene, home) in enumerate(zip(genes, homes, strict=True)):
        code, type_code = index.gene_code(gene), index.type_code(home) if home else -1
        if code < 0 or type_code < 0:
            continue
        hit = assigned & (index.gene_codes == code)
        hit[hit] = index.type_codes[index.cell_codes[hit]] == type_code
        default_counts[g] = int((hit & index.mask(ConditionName.DEFAULT)).sum())
        for condition in conditions:
            kept[condition][g] = int((hit & index.mask(condition)).sum())
    return default_counts, kept


def _closer_to_home(index: _Index, molecules: np.ndarray, homes: list[str | None]) -> np.ndarray:
    """For each molecule: strictly closer to the nearest centroid of its gene's home cell type than to its own
    cell's centroid. A molecule whose own cell is the nearest home cell is not closer (the distances are equal)."""
    closer = np.zeros(len(molecules), dtype=bool)
    if not len(molecules):
        return closer
    homes_arr = np.array([h or "" for h in homes], dtype=object)
    own = index.cell_codes[molecules]
    own_distance = np.hypot(index.x[molecules] - index.cell_x[own], index.y[molecules] - index.cell_y[own])
    for home in {h for h in homes if h}:
        type_code = index.type_code(home)
        rows = np.flatnonzero(homes_arr == home)
        if type_code < 0:
            continue
        centroids = np.flatnonzero(index.type_codes == type_code)
        tree = cKDTree(np.column_stack([index.cell_x[centroids], index.cell_y[centroids]]))
        distance, _ = tree.query(np.column_stack([index.x[molecules[rows]], index.y[molecules[rows]]]), k=1, workers=-1)
        closer[rows] = distance < own_distance[rows]
    return closer


# --- pooling and labels -----------------------------------------------------------------------------------------


def _pool(audits: Sequence[_SectionAudit], condition: ConditionName, measure: Measure) -> PooledConditionValue:
    terms = [a.terms[condition] for a in audits]
    cells = sum(a.values.cells_labelled for a in audits)
    molecules = sum(t.molecules for t in terms)
    default_molecules = sum(t.default_molecules for t in terms)
    reasons: dict[str, str] = {}
    if not audits:
        reasons["observed_value"] = "no eligible sections"
        return PooledConditionValue(condition=condition, cells=0, molecules=0, default_molecules=0, retention=None,
                                    observed_value=None, expectation_cell_matched=None, expectation_home_matched=None,
                                    excess_drop_cell_matched=None, excess_drop_home_matched=None, missing_reasons=reasons)
    total = lambda name: np.sum([getattr(t, name) for t in terms], axis=0)  # noqa: E731
    home_missing = any(t.home_num is None for t in terms)
    if measure == "co_expression_score":
        default_terms = [a.terms[ConditionName.DEFAULT] for a in audits]
        supported = np.sum([t.observed_den for t in default_terms], axis=0) > 0
        observed = _pair_mean(total("observed_num"), total("observed_den"), supported)
        e_cell = _pair_mean(total("cell_num"), total("cell_den"), supported)
        e_home = None if home_missing else _pair_mean(total("home_num"), total("home_den"), supported)
    else:
        den = float(total("observed_den")[0])
        observed = float(total("observed_num")[0]) / den if den else None
        e_cell = float(total("cell_num")[0]) / den if den else None
        e_home = None if (home_missing or not den) else float(total("home_num")[0]) / den
    if home_missing:
        reasons["expectation_home_matched"] = "an eligible section has no home-matched expectation"
    below = None if (observed is None or e_home is None) else bool(observed < e_home * THRESHOLD_FACTOR)
    return PooledConditionValue(
        condition=condition,
        cells=cells,
        molecules=molecules,
        default_molecules=default_molecules,
        retention=molecules / default_molecules if default_molecules else None,
        observed_value=observed,
        expectation_cell_matched=e_cell,
        expectation_home_matched=e_home,
        excess_drop_cell_matched=None if (observed is None or e_cell is None) else e_cell - observed,
        excess_drop_home_matched=None if (observed is None or e_home is None) else e_home - observed,
        below_home_threshold=None if condition == ConditionName.DEFAULT else below,
        missing_reasons=reasons,
    )


def _verdict(audits: Sequence[_SectionAudit], stricter: Sequence[ConditionName], measure: Measure) -> tuple[list[ConditionName], EvidenceStatus | None]:
    pooled = [_pool(audits, c, measure) for c in stricter]
    if any(p.below_home_threshold is None for p in pooled):
        return [], None
    below = [p.condition for p in pooled if p.below_home_threshold]
    return below, EvidenceStatus.SEGMENTATION_SENSITIVE if below else EvidenceStatus.STABLE


def _label(
    eligible: list[_SectionAudit], n_sections: int, cell_type: str, genes: list[str], measure: Measure,
    stricter: list[ConditionName], no_home: list[str],
) -> tuple[EvidenceStatus, str, list[LeaveOneSectionOutVerdict]]:
    insufficient = EvidenceStatus.INSUFFICIENT_EVIDENCE
    if len(eligible) < MIN_ELIGIBLE_SECTIONS:
        return insufficient, (
            f"{len(eligible)} of {n_sections} sections are eligible; an audit result needs at least {MIN_ELIGIBLE_SECTIONS}. "
            f"A section is eligible with at least {POPULATION_GATE_MIN_CELLS} cells labelled {cell_type} and at least "
            f"{MOLECULE_GATE_MIN_MOLECULES} of the result's molecules in them under the default condition."
        ), []
    if no_home:
        return insufficient, f"{', '.join(no_home)} has no home cell type, so there is no home-matched expectation.", []
    if not stricter:
        return insufficient, "No stricter primary condition was computed.", []
    full_below, full_verdict = _verdict(eligible, stricter, measure)
    loo = []
    for audit in eligible:
        rest = [a for a in eligible if a is not audit]
        below, verdict = _verdict(rest, stricter, measure)
        loo.append(LeaveOneSectionOutVerdict(left_out_section_id=audit.values.section_id, conditions_below_threshold=below, verdict=verdict))
    if full_verdict is None or any(v.verdict is None for v in loo):
        return insufficient, "A home-matched expectation is missing in an eligible section.", loo
    threshold = f"the home-matched expectation x 2^-{EXCESS_LOG2_DROP}"
    persistent = [c for c in full_below if all(c in v.conditions_below_threshold for v in loo)]
    if persistent:
        names = ", ".join(c.value for c in persistent)
        return EvidenceStatus.SEGMENTATION_SENSITIVE, (
            f"Pooled over {len(eligible)} eligible sections, the observed value falls below {threshold} under {names}, "
            "and still does with any one eligible section left out."
        ), loo
    if not full_below and all(not v.conditions_below_threshold for v in loo):
        return EvidenceStatus.STABLE, (
            f"Pooled over {len(eligible)} eligible sections, the observed value stays at or above {threshold} under every "
            "stricter primary condition, and still does with any one eligible section left out."
        ), loo
    flips = [v.left_out_section_id for v in loo if sorted(v.conditions_below_threshold) != sorted(full_below)]
    return insufficient, (
        f"The verdict is not consistent across leave-one-section-out: leaving out {', '.join(flips) or 'a section'} changes "
        f"which conditions fall below {threshold}."
    ), loo


# --- evidence regions -------------------------------------------------------------------------------------------


def _evidence_regions(audits: Sequence[_SectionAudit], condition: ConditionName) -> list[EvidenceRegion]:
    frames = []
    for audit in audits:
        if not len(audit.scope_x):
            continue
        frames.append(pd.DataFrame({
            "section_id": audit.values.section_id,
            "ix": np.floor(audit.scope_x / WINDOW_UM).astype(np.int64),
            "iy": np.floor(audit.scope_y / WINDOW_UM).astype(np.int64),
            "excluded": (~audit.kept[condition]).astype(np.int64),
            "default": 1,
        }))
    if not frames:
        return []
    windows = pd.concat(frames).groupby(["section_id", "ix", "iy"], as_index=False)[["excluded", "default"]].sum()
    windows = windows[windows["excluded"] > 0]
    windows = windows.sort_values(["excluded", "default", "section_id", "iy", "ix"], ascending=[False, False, True, True, True]).head(TOP_REGIONS)
    return [
        EvidenceRegion(
            rank=rank,
            region=Region(section_id=str(w.section_id), x0=w.ix * WINDOW_UM, y0=w.iy * WINDOW_UM, x1=(w.ix + 1) * WINDOW_UM, y1=(w.iy + 1) * WINDOW_UM),
            score=float(w.excluded),
            condition=condition,
            excluded_molecules=int(w.excluded),
            default_molecules=int(w.default),
        )
        for rank, w in enumerate(windows.itertuples(index=False), start=1)
    ]


# --- public operation -------------------------------------------------------------------------------------------


def audit_population(
    sections: Sequence[SectionTables],
    cell_type: str,
    genes: Sequence[str] = (),
    conditions: Sequence[ConditionName] = PRIMARY_CONDITIONS,
    *,
    measure: Measure | None = None,
    marker_pairs: MarkerPairs | None = None,
    section_groups: Mapping[str, str] | None = None,
    sections_left_out: Mapping[str, str] | None = None,
    roi: Region | None = None,
) -> AuditResult:
    """Audit one measure of one cell population across assignment conditions, per section, with both
    random-thinning expectations, neighbour-proximity shares, evidence regions and the frozen audit label.

    `genes`: one gene (share expressing) or several (presence of any). For `measure="co_expression_score"` the
    pairs come from `marker_pairs` (the frozen artifact by default), or from `genes` when it names one pair.
    `sections_left_out` lists dataset sections not counted, with the reason (for example a duplicate).
    With an `roi`, the one section on it is cut to the box first (see `restrict_to_roi`).
    """
    if ConditionName.DEFAULT not in conditions:
        raise ValueError("the default condition is required: populations and retention are fixed under it")
    if len({(s.dataset_id, s.label_rule_id) for s in sections}) != 1:
        raise ValueError("an audit result covers sections of one dataset under one label rule")
    conditions = [ConditionName.DEFAULT] + [c for c in conditions if c != ConditionName.DEFAULT]
    marker_pairs = marker_pairs or load_marker_pairs()
    if measure is None:
        measure = "share_expressing" if len(genes) == 1 else "gene_set_share_expressing"
    if measure == "co_expression_score":
        pair_list = [tuple(sorted(genes))] if len(genes) == 2 else list(marker_pairs.pairs)
        genes = sorted({g for pair in pair_list for g in pair})
        pairs = [(genes.index(a), genes.index(b)) for a, b in pair_list]
    else:
        if not genes:
            raise ValueError("a presence measure needs at least one gene")
        genes, pair_list, pairs = list(genes), [], []
    if roi is not None:
        matching = [s for s in sections if s.section_id == roi.section_id]
        if len(matching) != 1 or len(sections) != 1:
            raise ValueError("an ROI-scoped audit covers exactly the one section the ROI is on")
        sections = [restrict_to_roi(matching[0], roi)]

    groups = dict(section_groups or {})
    audits = [_audit_one(s, cell_type, genes, measure, pairs, conditions, groups.get(s.section_id)) for s in sections]
    eligible = [a for a in audits if a.eligible]
    stricter = [c for c in conditions if c in PRIMARY_CONDITIONS and c != ConditionName.DEFAULT]
    result_genes = [g for g in genes if measure != "co_expression_score" or HOME_CELL_TYPES.get(g) != cell_type]
    no_home = [g for g in result_genes if HOME_CELL_TYPES.get(g) is None]
    label, reason, loo = _label(eligible, len(audits), cell_type, genes, measure, stricter, no_home)
    ranking_condition = next((c for c in (ConditionName.NUCLEUS_ONLY, ConditionName.DISTANCE_CAP_1UM, ConditionName.DISTANCE_CAP_2UM) if c in conditions), None)
    by_group: dict[str, int] = {}
    for audit in eligible:
        key = audit.values.group or "unknown"
        by_group[key] = by_group.get(key, 0) + 1

    result = AuditResult(
        finding_id="pending",
        dataset_id=sections[0].dataset_id,
        population=Population(label_rule_id=sections[0].label_rule_id, cell_type=cell_type),
        genes=genes,
        measure=measure,
        sections=[a.values for a in audits],
        eligible_section_ids=[a.values.section_id for a in eligible],
        evidence_regions=_evidence_regions(eligible or audits, ranking_condition) if ranking_condition else [],
        ranking_rule=ranking_rule(ranking_condition) if ranking_condition else None,
        label=label,
        label_reason=reason,
        gene_pairs=[list(p) for p in pair_list],
        marker_pairs=marker_pairs.source,
        pooled=[_pool(eligible, c, measure) for c in conditions],
        leave_one_section_out=loo,
        eligible_by_group=dict(sorted(by_group.items())),
        sections_left_out=[LeftOutSection(section_id=k, reason=v) for k, v in sorted((sections_left_out or {}).items())],
        rules=AuditRules(
            population_gate_min_cells=POPULATION_GATE_MIN_CELLS,
            molecule_gate_min_molecules=MOLECULE_GATE_MIN_MOLECULES,
            min_eligible_sections=MIN_ELIGIBLE_SECTIONS,
            excess_log2_drop_threshold=EXCESS_LOG2_DROP,
            home_label_rule_id=sections[0].label_rule_id,
            home_cell_types={g: HOME_CELL_TYPES.get(g) for g in genes},
            result_molecules_rule=result_molecules_rule(measure),
            pooling_rule=POOLING_RULE,
            label_rule=LABEL_RULE,
            expectation_rule=EXPECTATION_RULE,
        ),
        roi=roi,
    )
    return result.model_copy(update={"finding_id": content_id("fnd", result.model_dump(mode="json", exclude={"finding_id"}))})
