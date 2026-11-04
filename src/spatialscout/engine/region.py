"""Build a region view: a section's molecules, nuclei and structure outlines as compact columns."""

import base64
import math
from collections.abc import Sequence
from typing import Literal

import numpy as np
import pandas as pd

from ..contracts import (
    CellColumns,
    ConditionName,
    MoleculeColumns,
    PackedCellColumns,
    PackedColumn,
    PackedMoleculeColumns,
    PackedRegionView,
    Region,
    RegionView,
)
from ..data import SectionTables
from .conditions import inclusion_mask

APPROXIMATE_NUCLEI = "Nuclei are drawn as circles with each nucleus's area: an approximation, not a measured boundary."


def build_region_view(section: SectionTables, conditions: Sequence[ConditionName], *, synthetic: bool) -> RegionView:
    """The whole section as one region view, with per-condition inclusion bits for every molecule."""
    molecules, cells = section.molecules, section.cells
    genes = sorted(molecules["gene"].astype(str).unique())
    cell_types = sorted(cells["cell_type"].astype(str).unique())
    cell_position = {cell_id: i for i, cell_id in enumerate(cells["cell_id"].astype(str))}
    gene_position = {gene: i for i, gene in enumerate(genes)}
    type_position = {cell_type: i for i, cell_type in enumerate(cell_types)}
    cell_ids = molecules["cell_id"].astype("string").fillna("").to_numpy(dtype=object)
    xs = np.concatenate([molecules["x"].to_numpy(), cells["x"].to_numpy()])
    ys = np.concatenate([molecules["y"].to_numpy(), cells["y"].to_numpy()])
    notes = [APPROXIMATE_NUCLEI]
    if synthetic:
        notes.insert(0, "Synthetic section: answers known by construction, not measured in tissue.")
    return RegionView(
        dataset_id=section.dataset_id,
        section_id=section.section_id,
        synthetic=synthetic,
        region=Region(section_id=section.section_id, x0=float(xs.min()), y0=float(ys.min()), x1=float(xs.max()), y1=float(ys.max())),
        label_rule_id=section.label_rule_id,
        genes=genes,
        cell_types=cell_types,
        molecules=MoleculeColumns(
            x=[round(float(v), 3) for v in molecules["x"]],
            y=[round(float(v), 3) for v in molecules["y"]],
            gene_index=[gene_position[g] for g in molecules["gene"].astype(str)],
            cell_index=[cell_position.get(c, -1) for c in cell_ids],
            included={c: inclusion_mask(section, c).astype(int).tolist() for c in conditions},
        ),
        cells=CellColumns(
            cell_id=list(cells["cell_id"].astype(str)),
            x=[float(v) for v in cells["x"]],
            y=[float(v) for v in cells["y"]],
            nucleus_radius=[round(math.sqrt(float(a) / math.pi), 3) for a in cells["nucleus_area"]],
            cell_type_index=[type_position[t] for t in cells["cell_type"].astype(str)],
        ),
        structures=list(section.structures),
        notes=notes,
    )


def build_packed_region_view(
    section: SectionTables,
    conditions: Sequence[ConditionName],
    *,
    synthetic: bool,
    section_name: str | None = None,
    group: str | None = None,
) -> PackedRegionView:
    """The whole section as typed little-endian columns, built without per-molecule Python loops, so a section
    of millions of molecules packs in about a second. Each condition owns one bit of `inclusion_bits`."""
    if len(conditions) > 8:
        raise ValueError("inclusion bits hold at most 8 conditions")
    molecules, cells = section.molecules, section.cells
    genes = sorted(molecules["gene"].astype(str).unique())
    cell_types = sorted(cells["cell_type"].astype(str).unique())
    if len(genes) > 256 or len(cell_types) > 256:
        raise ValueError("gene and cell type indexes are uint8: at most 256 of each")
    gene_index = pd.Categorical(molecules["gene"].astype(str), categories=genes).codes
    cell_index = pd.Index(cells["cell_id"].astype(str)).get_indexer(molecules["cell_id"].astype("string").fillna("").astype(str))
    bits = np.zeros(len(molecules), dtype=np.uint8)
    for bit, condition in enumerate(conditions):
        bits |= inclusion_mask(section, condition).astype(np.uint8) << np.uint8(bit)
    radius = np.sqrt(cells["nucleus_area"].to_numpy(dtype=float) / math.pi)
    xs = np.concatenate([molecules["x"].to_numpy(dtype=float), cells["x"].to_numpy(dtype=float)])
    ys = np.concatenate([molecules["y"].to_numpy(dtype=float), cells["y"].to_numpy(dtype=float)])
    notes = [APPROXIMATE_NUCLEI, "A cell with no detected nucleus has no ring."]
    if synthetic:
        notes.insert(0, "Synthetic section: answers known by construction, not measured in tissue.")
    return PackedRegionView(
        dataset_id=section.dataset_id,
        section_id=section.section_id,
        section_name=section_name,
        group=group,
        synthetic=synthetic,
        region=Region(section_id=section.section_id, x0=float(np.nanmin(xs)), y0=float(np.nanmin(ys)), x1=float(np.nanmax(xs)), y1=float(np.nanmax(ys))),
        label_rule_id=section.label_rule_id,
        genes=genes,
        cell_types=cell_types,
        molecules=PackedMoleculeColumns(
            count=len(molecules),
            x=_pack(molecules["x"].to_numpy(), "float32"),
            y=_pack(molecules["y"].to_numpy(), "float32"),
            gene_index=_pack(gene_index, "uint8"),
            cell_index=_pack(cell_index, "int32"),
            inclusion_bits=_pack(bits, "uint8"),
            condition_bits={condition: bit for bit, condition in enumerate(conditions)},
        ),
        cells=PackedCellColumns(
            count=len(cells),
            cell_id=cells["cell_id"].astype(str).tolist(),
            x=_pack(cells["x"].to_numpy(), "float32"),
            y=_pack(cells["y"].to_numpy(), "float32"),
            nucleus_radius=_pack(np.nan_to_num(radius, nan=0.0), "float32"),
            cell_type_index=_pack(pd.Categorical(cells["cell_type"].astype(str), categories=cell_types).codes, "uint8"),
        ),
        structures=list(section.structures),
        notes=notes,
    )


def _pack(values: np.ndarray, dtype: Literal["float32", "uint8", "int32"]) -> PackedColumn:
    little_endian = np.ascontiguousarray(values, dtype=np.dtype(dtype).newbyteorder("<"))
    return PackedColumn(dtype=dtype, data=base64.b64encode(little_endian.tobytes()).decode("ascii"))
