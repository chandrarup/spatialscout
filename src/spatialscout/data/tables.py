"""Validated in-memory tables for one section: its molecules and its cells.

Columns follow the GSE286184 deposit, renamed to glossary terms: `gene` is the Xenium `feature_name`,
`x`/`y` are micrometres, and an unassigned molecule has a null `cell_id` (Xenium writes "UNASSIGNED").
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

import pandas as pd

from ..contracts import StructureMask

MOLECULE_COLUMNS: dict[str, str] = {
    "molecule_id": "string",
    "gene": "string",
    "x": "float64",
    "y": "float64",
    "cell_id": "string",
    "overlaps_nucleus": "bool",
    "nucleus_distance": "float64",
    "qv": "float64",
}

CELL_COLUMNS: dict[str, str] = {
    "cell_id": "string",
    "cell_type": "string",
    "x": "float64",
    "y": "float64",
    "nucleus_area": "float64",
    "cell_area": "float64",
}


@dataclass(frozen=True)
class SectionTables:
    """One section's molecules and cells. Cell type labels are already assigned and frozen."""

    section_id: str
    dataset_id: str
    molecules: pd.DataFrame
    cells: pd.DataFrame
    structures: tuple[StructureMask, ...] = ()


def make_section(
    section_id: str,
    dataset_id: str,
    molecules: pd.DataFrame | Iterable[Mapping[str, Any]],
    cells: pd.DataFrame | Iterable[Mapping[str, Any]],
    structures: Iterable[StructureMask] = (),
) -> SectionTables:
    """Build a section from records or data frames, checking every required column is present."""
    return SectionTables(
        section_id=section_id,
        dataset_id=dataset_id,
        molecules=_typed_table(molecules, MOLECULE_COLUMNS, "molecules"),
        cells=_typed_table(cells, CELL_COLUMNS, "cells"),
        structures=tuple(structures),
    )


def _typed_table(rows: pd.DataFrame | Iterable[Mapping[str, Any]], columns: dict[str, str], name: str) -> pd.DataFrame:
    frame = rows.copy() if isinstance(rows, pd.DataFrame) else pd.DataFrame.from_records(list(rows), columns=None)
    missing = [c for c in columns if c not in frame.columns]
    if missing:
        raise ValueError(f"{name} table is missing columns: {', '.join(missing)}")
    return frame[list(columns)].astype(columns).reset_index(drop=True)
