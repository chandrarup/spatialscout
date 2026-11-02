"""Build a region view: a section's molecules, nuclei and structure outlines as compact columns."""

import math
from collections.abc import Sequence

import numpy as np

from ..contracts import CellColumns, ConditionName, MoleculeColumns, Region, RegionView
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
