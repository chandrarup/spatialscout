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
    mask_version: str | None = Field(default=None, description="SAM 3.1 outlines: the version of the finder's frozen rules.")
    run_id: str | None = Field(default=None, description="SAM 3.1 outlines: the structure-finder run that proposed it.")
    seed_id: str | None = Field(default=None, description="SAM 3.1 outlines: the seed box it was prompted with.")


class StructureSeed(Contract):
    """One box prompt: merged NPHS1 clusters (one per glomerulus, padded), or a box the researcher drew.
    NPHS1 seeds the box, so it is never used to judge the outline."""

    seed_id: str
    section_id: str
    origin: Literal["nphs1_clusters", "user_box"]
    box: Region
    nphs1_molecules: int | None = Field(default=None, description="NPHS1 molecules in the merged clusters; null for a user box.")
    clusters_merged: int | None = Field(default=None, description="NPHS1 clusters merged into this seed; null for a user box.")


class OutlineMeasures(Contract):
    """One candidate outline of a seed (the seed box, the convex hull of its NPHS1 clusters, or the SAM 3.1
    outline) measured the same way, so what SAM adds over the cruder shapes is visible.

    - `seed_box_coverage`: the share of the seed box's area the shape covers.
    - `retention`: the structure-constrained condition with this shape as the only structure, over default
      molecules whose molecule or cell centroid lies inside it: the share kept.
    - PECAM1 (endothelium) and PDGFRB (mesangium) consistency: each gene's molecule density inside the shape over
      its density in the rest of the seed's crop, and the share of the crop's molecules of the gene inside.
      Glomerular tufts carry both; neither gene seeded the box.
    """

    shape: Literal["seed_box", "convex_hull", "sam_outline"]
    area_um2: float | None
    seed_box_coverage: float | None
    default_molecules: int
    kept_molecules: int
    retention: float | None
    pecam1_enrichment: float | None
    pdgfrb_enrichment: float | None
    pecam1_share_inside: float | None
    pdgfrb_share_inside: float | None
    missing_reasons: dict[str, str] = Field(default_factory=dict)


class StructureProposal(Contract):
    """What SAM 3.1 proposed for one seed. Empty, fragmented and rejected proposals are kept, never forced:
    - outlined: one connected piece that passes the geometric checks;
    - fragmented: several pieces; the largest is outlined and the count recorded;
    - empty: no mask came back, or it has no pixels;
    - rejected: a geometric check failed (see the run's `rejection_rule`), or the seed was never sent.
    """

    seed: StructureSeed
    status: Literal["outlined", "fragmented", "empty", "rejected"]
    reason: str | None = None
    structure_id: str | None = Field(default=None, description="The structure mask built from it; null when it is empty or rejected.")
    fragments: int = 0
    crop_index: int | None = Field(default=None, description="The image it was sent in, by index into the run's crops.")
    comparisons: list[OutlineMeasures]


class StructureRun(Contract):
    """One run of the structure finder on one section: the images sent to SAM 3.1, what came back for every seed,
    and the outlines kept. Exploratory (ADR-0006): the outlines feed only the structure-constrained condition,
    which never enters an evidence label."""

    schema_version: str = SCHEMA_VERSION
    run_id: str
    mask_version: str
    dataset_id: str
    section_id: str
    model: str
    run_mode: Literal["cached_tool_rerun", "live"]
    badge: Literal["SAM 3.1 proposal (exploratory)"] = "SAM 3.1 proposal (exploratory)"
    seeding_rule: str
    rendering_rule: str
    rejection_rule: str
    images_sent: int
    estimated_cost_usd: float = Field(description="Live spend for a live run; for a stored run, what the same images cost at list price.")
    crops: list[Region]
    proposals: list[StructureProposal]
    structures: list[StructureMask]


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


class PackedColumn(Contract):
    """One column as a base64 string of little-endian values, decoded straight into a typed array."""

    dtype: Literal["float32", "uint8", "int32"]
    data: str


class PackedMoleculeColumns(Contract):
    """Every molecule of the view, one typed column each."""

    count: int
    x: PackedColumn = Field(description="float32 micrometres.")
    y: PackedColumn = Field(description="float32 micrometres.")
    gene_index: PackedColumn = Field(description="uint8 index into PackedRegionView.genes.")
    cell_index: PackedColumn = Field(description="int32 index into the cell columns; -1 for an unassigned molecule.")
    inclusion_bits: PackedColumn = Field(
        description="uint8 per molecule: bit condition_bits[c] is set when the molecule counts toward its cell under c."
    )
    condition_bits: dict[ConditionName, int]


class PackedCellColumns(Contract):
    count: int
    cell_id: list[str]
    x: PackedColumn = Field(description="float32 centroid, micrometres.")
    y: PackedColumn = Field(description="float32 centroid, micrometres.")
    nucleus_radius: PackedColumn = Field(
        description="float32 radius of a circle with the nucleus's area (an approximation); 0 for a cell with no detected nucleus."
    )
    cell_type_index: PackedColumn = Field(description="uint8 index into PackedRegionView.cell_types.")


class PackedRegionView(Contract):
    """A region view in typed columns, compact enough to ship and draw a whole section of several hundred
    thousand molecules at once."""

    schema_version: str = SCHEMA_VERSION
    encoding: Literal["base64-little-endian-v1"] = "base64-little-endian-v1"
    dataset_id: str
    section_id: str
    section_name: str | None = None
    group: str | None = None
    synthetic: bool
    region: Region
    label_rule_id: str
    genes: list[str]
    cell_types: list[str]
    molecules: PackedMoleculeColumns
    cells: PackedCellColumns
    structures: list[StructureMask]
    notes: list[str]
