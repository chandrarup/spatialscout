"""The independent recompute: every number an audit claim can cite, rebuilt from the stored molecule tables.

This is a second code path, written apart from the analysis engine (`engine/population.py`, `engine/conditions.py`)
and sharing none of its code: plain pandas group-bys over the molecule and cell tables, with the assignment
conditions re-derived from the molecule flags (ADR-0002) and the frozen rules restated below. It is what the
numerical check compares a claim's cited numbers with, within the declared tolerances.

The result mirrors an audit result's shape (`sections[...]`, `pooled[...]`, `eligible_section_ids`) as attribute
dictionaries, so a claim's cited sources resolve in it with the same path grammar (`verify/citations.py`).
"""

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from ..data import SectionTables
from ..data.label_rules import MARKERS

# The frozen rules, restated (spec "frozen analysis rules").
MIN_POPULATION_CELLS = 20
MIN_RESULT_MOLECULES = 10
MIN_ELIGIBLE_SECTIONS = 3
THRESHOLD = 2.0**-0.5
DISTANCE_CAPS_UM = {"distance_cap_1um": 1.0, "distance_cap_2um": 2.0}
STRICTER = ("nucleus_only", "distance_cap_1um", "distance_cap_2um")
HOME_OF = {gene: cell_type for cell_type, genes in MARKERS.items() for gene in genes}

# The numerical check's declared tolerances: counts must match exactly; a fraction within FRACTION_ABS, or within
# the rounding the claim's written precision implies, whichever is larger.
TOLERANCES = {"count_abs": 0.0, "fraction_abs": 1e-6}


class Node(dict):
    """A dict whose keys also read as attributes, so `verify.citations.resolve_source` walks it like a contract."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name) from None


def recompute_audit(
    sections: Sequence[SectionTables],
    cell_type: str,
    genes: Sequence[str],
    measure: str,
    conditions: Sequence[str],
    gene_pairs: Sequence[Sequence[str]] = (),
    roi: Any = None,
) -> Node:
    """Recompute an audit result's per-section and pooled values. `conditions` are condition names (default first)."""
    conditions = [str(c) for c in conditions]
    genes = list(genes)
    pairs = [tuple(p) for p in gene_pairs] if measure == "co_expression_score" else []
    result_genes = [g for g in genes if measure != "co_expression_score" or HOME_OF.get(g) != cell_type]
    per_section = [_section(s, cell_type, genes, result_genes, measure, pairs, conditions, roi) for s in sections]
    eligible = [p for p in per_section if p["eligible"]]
    pooled = [_pooled(eligible, c, measure, pairs) for c in conditions]
    return Node(
        sections=[p["values"] for p in per_section],
        eligible_section_ids=[p["values"]["section_id"] for p in eligible],
        pooled=pooled,
        direction=direction_of(pooled),
    )


def direction_of(pooled: Sequence[Mapping[str, Any]]) -> str | None:
    """holds when the pooled observed value stays at or above the home-matched expectation x 2^-0.5 under every
    stricter condition; drops when it falls below under one; None when a value is missing."""
    below = []
    for value in pooled:
        if value["condition"] not in STRICTER:
            continue
        observed, expected = value["observed_value"], value["expectation_home_matched"]
        if observed is None or expected is None:
            return None
        below.append(observed < expected * THRESHOLD)
    if not below:
        return None
    return "drops" if any(below) else "holds"


# --- one section ---------------------------------------------------------------------------------------------


def _kept(molecules: pd.DataFrame, condition: str) -> pd.Series:
    """Which assigned molecules count toward their cell under the condition, re-derived from the molecule flags."""
    nuclear = molecules["overlaps_nucleus"].astype(bool)
    if condition == "default":
        return pd.Series(True, index=molecules.index)
    if condition == "nucleus_only":
        return nuclear
    if condition in DISTANCE_CAPS_UM:
        return nuclear | (molecules["nucleus_distance"].astype(float) <= DISTANCE_CAPS_UM[condition]).fillna(False)
    raise ValueError(f"the independent recompute does not cover condition {condition!r}")


def _section(section, cell_type, genes, result_genes, measure, pairs, conditions, roi) -> dict[str, Any]:
    cells = section.cells[["cell_id", "cell_type", "x", "y"]].copy()
    cells["cell_id"] = cells["cell_id"].astype(str)
    cells["cell_type"] = cells["cell_type"].astype(str)
    if roi is not None:
        cells = cells[(cells.x >= roi.x0) & (cells.x <= roi.x1) & (cells.y >= roi.y0) & (cells.y <= roi.y1)]
    molecules = section.molecules[["gene", "x", "y", "cell_id", "overlaps_nucleus", "nucleus_distance"]]
    molecules = molecules[molecules["cell_id"].notna()].copy()
    molecules["cell_id"] = molecules["cell_id"].astype(str)
    molecules["gene"] = molecules["gene"].astype(str)
    molecules = molecules[molecules["cell_id"].isin(set(cells["cell_id"]))]
    type_of = dict(zip(cells["cell_id"], cells["cell_type"], strict=True))
    molecules["cell_type"] = molecules["cell_id"].map(type_of)
    for condition in conditions:
        molecules[f"kept:{condition}"] = _kept(molecules, condition).to_numpy()

    population = cells.loc[cells["cell_type"] == cell_type, "cell_id"].tolist()
    n_cells = len(population)
    in_population = molecules[molecules["cell_type"] == cell_type]
    of_genes = in_population[in_population["gene"].isin(genes)]
    of_result = of_genes[of_genes["gene"].isin(result_genes)]
    n_default = len(of_result)

    # Default molecules of each gene per population cell, and of every gene per population cell.
    k = of_genes.groupby(["cell_id", "gene"]).size().unstack(fill_value=0).reindex(index=population, columns=genes, fill_value=0)
    all_default = in_population.groupby("cell_id").size().reindex(population, fill_value=0)

    # Home-matched retention per gene: kept over default molecules of the gene in cells of its home type.
    home_rows = molecules[molecules["gene"].isin(genes)]
    home_rows = home_rows[home_rows["cell_type"] == home_rows["gene"].map(HOME_OF)]

    # Neighbour-proximity: is each result molecule strictly closer to a home-type centroid than to its own cell's?
    closer = _closer_to_home(of_result, cells)

    rows = []
    terms = {}
    for condition in conditions:
        flag = f"kept:{condition}"
        kk = of_genes[of_genes[flag]].groupby(["cell_id", "gene"]).size().unstack(fill_value=0).reindex(
            index=population, columns=genes, fill_value=0
        )
        kept_all = in_population[in_population[flag]].groupby("cell_id").size().reindex(population, fill_value=0)
        r_cell = (kept_all / all_default.replace(0, np.nan)).fillna(0.0).to_numpy()
        p_cell = 1.0 - np.power(1.0 - r_cell[:, None], k.to_numpy())
        rho = {}
        for gene in genes:
            rows_g = home_rows[home_rows["gene"] == gene]
            rho[gene] = rows_g[flag].sum() / len(rows_g) if len(rows_g) else None
        missing_home = [g for g in genes if rho[g] is None and k[g].sum() > 0]
        p_home = None if missing_home else 1.0 - np.power(1.0 - np.array([[rho[g] or 0.0 for g in genes]]), k.to_numpy())

        n_kept = int(of_result[flag].sum())
        if measure == "co_expression_score":
            expressed, kept_expr = k.to_numpy() > 0, kk.to_numpy() > 0
            idx = {g: i for i, g in enumerate(genes)}
            pair_terms = []
            for a, b in pairs:
                ia, ib = idx[a], idx[b]
                supported = bool((expressed[:, ia] | expressed[:, ib]).any())
                both = float((kept_expr[:, ia] & kept_expr[:, ib]).sum())
                either = float((kept_expr[:, ia] | kept_expr[:, ib]).sum())
                cell = (float((p_cell[:, ia] * p_cell[:, ib]).sum()), float((p_cell[:, ia] + p_cell[:, ib] - p_cell[:, ia] * p_cell[:, ib]).sum()))
                home = None if p_home is None else (
                    float((p_home[:, ia] * p_home[:, ib]).sum()), float((p_home[:, ia] + p_home[:, ib] - p_home[:, ia] * p_home[:, ib]).sum())
                )
                pair_terms.append({"supported": supported, "both": both, "either": either, "cell": cell, "home": home})
            terms[condition] = {"pairs": pair_terms, "molecules": n_kept, "default": n_default, "cells": n_cells}
            observed = _pair_mean([(t["both"], t["either"]) for t in pair_terms], [t["supported"] for t in pair_terms])
            e_cell = _pair_mean([t["cell"] for t in pair_terms], [t["supported"] for t in pair_terms])
            e_home = None if p_home is None else _pair_mean([t["home"] for t in pair_terms], [t["supported"] for t in pair_terms])
            cells_expressing = None
        else:
            cells_expressing = int((kk.to_numpy() > 0).any(axis=1).sum())
            cell_sum = float((1.0 - np.prod(1.0 - p_cell, axis=1)).sum())
            home_sum = None if p_home is None else float((1.0 - np.prod(1.0 - p_home, axis=1)).sum())
            terms[condition] = {"expressing": cells_expressing, "cell": cell_sum, "home": home_sum, "molecules": n_kept,
                                "default": n_default, "cells": n_cells}
            observed = cells_expressing / n_cells if n_cells else None
            e_cell = cell_sum / n_cells if n_cells else None
            e_home = home_sum / n_cells if (n_cells and home_sum is not None) else None

        excluded = ~of_result[flag].to_numpy()
        rows.append(Node(
            condition=condition,
            molecules=n_kept,
            retention=n_kept / n_default if n_default else None,
            observed_value=observed,
            cells_expressing=cells_expressing,
            expectation_cell_matched=e_cell,
            expectation_home_matched=e_home,
            excess_drop_cell_matched=None if (e_cell is None or observed is None) else e_cell - observed,
            excess_drop_home_matched=None if (e_home is None or observed is None) else e_home - observed,
            neighbour_proximity_share_excluded=float(closer[excluded].mean()) if excluded.any() else None,
            neighbour_proximity_share_retained=float(closer[~excluded].mean()) if (~excluded).any() else None,
            nuclear_overlap_share=float(of_result.loc[of_result[flag], "overlaps_nucleus"].astype(bool).mean()) if n_kept else None,
        ))
    eligible = n_cells >= MIN_POPULATION_CELLS and n_default >= MIN_RESULT_MOLECULES
    values = Node(section_id=section.section_id, cells_labelled=n_cells, conditions=rows, eligible=eligible)
    return {"values": values, "terms": terms, "eligible": eligible}


def _closer_to_home(molecules: pd.DataFrame, cells: pd.DataFrame) -> np.ndarray:
    closer = np.zeros(len(molecules), dtype=bool)
    if not len(molecules):
        return closer
    position = cells.set_index("cell_id")[["x", "y"]]
    own = position.loc[molecules["cell_id"]].to_numpy()
    points = molecules[["x", "y"]].to_numpy(dtype=float)
    own_distance = np.sqrt(((points - own) ** 2).sum(axis=1))
    homes = molecules["gene"].map(HOME_OF).to_numpy(dtype=object)
    for home in {h for h in homes if isinstance(h, str)}:
        centroids = cells.loc[cells["cell_type"] == home, ["x", "y"]].to_numpy(dtype=float)
        if not len(centroids):
            continue
        rows = np.flatnonzero(homes == home)
        distance, _ = cKDTree(centroids).query(points[rows], k=1)
        closer[rows] = distance < own_distance[rows]
    return closer


def _pair_mean(terms: Sequence[tuple[float, float]], supported: Sequence[bool]) -> float | None:
    ratios = [num / den if den > 0 else 0.0 for (num, den), ok in zip(terms, supported, strict=True) if ok]
    return float(np.mean(ratios)) if ratios else None


# --- pooling -------------------------------------------------------------------------------------------------


def _pooled(eligible: Sequence[dict[str, Any]], condition: str, measure: str, pairs) -> Node:
    terms = [e["terms"][condition] for e in eligible]
    cells = sum(t["cells"] for t in terms)
    molecules = sum(t["molecules"] for t in terms)
    default = sum(t["default"] for t in terms)
    observed = e_cell = e_home = None
    if terms and measure == "co_expression_score":
        default_terms = [e["terms"]["default"] for e in eligible]
        n = len(pairs)
        supported = [sum(dt["pairs"][i]["either"] for dt in default_terms) > 0 for i in range(n)]
        observed = _pair_mean([(sum(t["pairs"][i]["both"] for t in terms), sum(t["pairs"][i]["either"] for t in terms)) for i in range(n)], supported)
        e_cell = _pair_mean([tuple(sum(t["pairs"][i]["cell"][j] for t in terms) for j in (0, 1)) for i in range(n)], supported)
        if all(t["pairs"][i]["home"] is not None for t in terms for i in range(n)):
            e_home = _pair_mean([tuple(sum(t["pairs"][i]["home"][j] for t in terms) for j in (0, 1)) for i in range(n)], supported)
    elif terms and cells:
        observed = sum(t["expressing"] for t in terms) / cells
        e_cell = sum(t["cell"] for t in terms) / cells
        if all(t["home"] is not None for t in terms):
            e_home = sum(t["home"] for t in terms) / cells
    return Node(
        condition=condition,
        cells=cells,
        molecules=molecules,
        default_molecules=default,
        retention=molecules / default if default else None,
        observed_value=observed,
        expectation_cell_matched=e_cell,
        expectation_home_matched=e_home,
        excess_drop_cell_matched=None if (observed is None or e_cell is None) else e_cell - observed,
        excess_drop_home_matched=None if (observed is None or e_home is None) else e_home - observed,
    )
