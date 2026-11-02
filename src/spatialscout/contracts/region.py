"""Tissue geometry contracts: structure masks and the region view the viewer draws."""

from typing import Literal

from pydantic import Field

from .base import SCHEMA_VERSION, ConditionName, Contract
from .finding import Region


class StructureMask(Contract):
    """The outline of one structure in section coordinates (micrometres), as a closed polygon.

    `source` says where the outline came from: drawn by construction in a synthetic fixture, or proposed
    by SAM 3.1 from a box prompt (ADR-0005), which the UI must label as a proposal.
    """

    schema_version: str = SCHEMA_VERSION
    structure_id: str
    section_id: str
    kind: Literal["glomerulus"]
    outline: list[list[float]]
    source: Literal["synthetic", "sam-3.1"]


class MoleculeColumns(Contract):
    """One entry per molecule, column by column, so a whole section ships compactly."""

    x: list[float]
    y: list[float]
    gene_index: list[int] = Field(description="Index into RegionView.genes.")
    cell_index: list[int] = Field(description="Index into the cell columns; -1 for an unassigned molecule.")
    included: dict[ConditionName, list[int]] = Field(
        description="Per condition, 1 if the molecule counts toward its cell under that condition, else 0."
    )


class CellColumns(Contract):
    cell_id: list[str]
    x: list[float]
    y: list[float]
    nucleus_radius: list[float] = Field(description="Radius of a circle with the nucleus's area: an approximation.")
    cell_type_index: list[int] = Field(description="Index into RegionView.cell_types.")


class RegionView(Contract):
    """Everything the viewer draws for one region of a section, in micrometres."""

    schema_version: str = SCHEMA_VERSION
    dataset_id: str
    section_id: str
    synthetic: bool
    region: Region
    label_rule_id: str
    genes: list[str]
    cell_types: list[str]
    molecules: MoleculeColumns
    cells: CellColumns
    structures: list[StructureMask]
    notes: list[str]
