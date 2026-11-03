"""Validate one raw Xenium section (GEO deposit columns) into molecule and cell tables.

Every raw molecule is either kept or counted under exactly one reason, checked in this order: malformed,
duplicate transcript id, below the quality threshold, not a panel gene. A kept molecule assigned to a cell
id the cells table lacks is counted as unmatched and kept as unassigned. Nothing is dropped silently.
"""

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..contracts import SectionValidation

MIN_QV = 20.0
"""Molecules need a quality score of at least 20 (Phred-scaled), as the spec's dataset store requires."""

UNASSIGNED = "UNASSIGNED"
"""What Xenium writes in `cell_id` for a molecule assigned to no cell."""

RAW_TRANSCRIPT_COLUMNS = ("transcript_id", "cell_id", "overlaps_nucleus", "feature_name", "x_location", "y_location", "qv", "nucleus_distance")
RAW_CELL_COLUMNS = ("cell_id", "x_centroid", "y_centroid", "nucleus_area", "cell_area")
VALIDATED_CELL_COLUMNS = ("cell_id", "x", "y", "nucleus_area", "cell_area")


class MalformedSection(ValueError):
    """A raw table lacks a required column, so the section cannot be validated at all."""


@dataclass(frozen=True)
class ValidatedSection:
    """Molecules in `MOLECULE_COLUMNS` order and cells (without labels yet), plus what validation did."""

    molecules: pd.DataFrame
    cells: pd.DataFrame
    validation: SectionValidation


def validate_section(transcripts: pd.DataFrame, cells: pd.DataFrame, panel: Iterable[str], min_qv: float = MIN_QV) -> ValidatedSection:
    _require(transcripts, RAW_TRANSCRIPT_COLUMNS, "transcripts")
    _require(cells, RAW_CELL_COLUMNS, "cells")
    cell_table, cell_counts = _validate_cells(cells)

    tx = transcripts.loc[:, list(RAW_TRANSCRIPT_COLUMNS)].reset_index(drop=True)
    numbers = tx[["x_location", "y_location", "qv", "nucleus_distance"]].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
    flag = pd.to_numeric(tx["overlaps_nucleus"], errors="coerce")
    malformed = (
        ~np.isfinite(numbers).all(axis=1)
        | ~flag.isin([0, 1]).to_numpy()
        | tx["feature_name"].isna().to_numpy()
        | tx["transcript_id"].isna().to_numpy()
        | tx["cell_id"].isna().to_numpy()
    )
    remaining = ~malformed
    # Malformed records are masked first, so a repeat of a malformed record is not a duplicate of a kept one.
    duplicate = remaining & tx["transcript_id"].astype("string").where(remaining).duplicated(keep="first").to_numpy()
    remaining &= ~duplicate
    below_quality = remaining & (numbers[:, 2] < min_qv)
    remaining &= ~below_quality
    not_in_panel = remaining & ~tx["feature_name"].astype("string").isin(set(panel)).to_numpy()
    remaining &= ~not_in_panel

    kept = tx[remaining]
    cell_ids = kept["cell_id"].astype("string")
    unassigned = cell_ids == UNASSIGNED
    unmatched = ~unassigned & ~cell_ids.isin(set(cell_table["cell_id"]))
    molecules = pd.DataFrame({
        "molecule_id": kept["transcript_id"].astype("string"),
        "gene": kept["feature_name"].astype("string"),
        "x": kept["x_location"].astype("float64"),
        "y": kept["y_location"].astype("float64"),
        "cell_id": cell_ids.where(~(unassigned | unmatched)),
        "overlaps_nucleus": flag[remaining].astype(bool),
        "nucleus_distance": kept["nucleus_distance"].astype("float64"),
        "qv": kept["qv"].astype("float64"),
    }).reset_index(drop=True)

    assigned_cells = set(molecules["cell_id"].dropna())
    validation = SectionValidation(
        molecules_read=len(tx),
        malformed_molecules=int(malformed.sum()),
        duplicate_molecules=int(duplicate.sum()),
        below_quality=int(below_quality.sum()),
        not_in_panel=int(not_in_panel.sum()),
        molecules_kept=len(molecules),
        unassigned_molecules=int(unassigned.sum()),
        unmatched_molecules=int(unmatched.sum()),
        cells_without_molecules=int((~cell_table["cell_id"].isin(assigned_cells)).sum()),
        **cell_counts,
    )
    return ValidatedSection(molecules=molecules, cells=cell_table, validation=validation)


def _validate_cells(cells: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    raw = cells.loc[:, list(RAW_CELL_COLUMNS)].reset_index(drop=True)
    numbers = raw[["x_centroid", "y_centroid", "cell_area"]].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
    malformed = ~np.isfinite(numbers).all(axis=1) | raw["cell_id"].isna().to_numpy()
    # Xenium leaves nucleus_area empty for a cell with no detected nucleus: a real cell, kept and counted.
    nucleus_area = pd.to_numeric(raw["nucleus_area"], errors="coerce")
    ids = raw["cell_id"].astype("string").where(~malformed)
    duplicate = ~malformed & ids.duplicated(keep="first").to_numpy()
    kept = raw[~malformed & ~duplicate]
    table = pd.DataFrame({
        "cell_id": kept["cell_id"].astype("string"),
        "x": kept["x_centroid"].astype("float64"),
        "y": kept["y_centroid"].astype("float64"),
        "nucleus_area": nucleus_area[~malformed & ~duplicate].astype("float64"),
        "cell_area": kept["cell_area"].astype("float64"),
    }).reset_index(drop=True)
    counts = {"cells_read": len(raw), "malformed_cells": int(malformed.sum()), "duplicate_cells": int(duplicate.sum()), "cells_kept": len(table),
              "cells_without_nucleus": int(table["nucleus_area"].isna().sum())}
    return table, counts


def _require(frame: pd.DataFrame, columns: Iterable[str], name: str) -> None:
    missing = [c for c in columns if c not in frame.columns]
    if missing:
        raise MalformedSection(f"the raw {name} table is missing columns: {', '.join(missing)}")
