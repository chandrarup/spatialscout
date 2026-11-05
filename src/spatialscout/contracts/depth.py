"""Contracts for measured molecule depth: a visualisation-side sidecar joined to a section's validated molecules by
transcript id, the bounded point sample a 3D view draws, and the descriptive depth profile of a box. None of this
feeds an audit, a claim or a recording; it is new descriptive exploration with its own identity."""

from typing import Literal

from pydantic import Field

from .base import SCHEMA_VERSION, Contract
from .finding import Region

DEPTH_VERSION = "depth-sidecar-v1"


class DepthSource(Contract):
    """Where a section's depths come from and how complete they are."""

    schema_version: str = SCHEMA_VERSION
    depth_version: str = DEPTH_VERSION
    dataset_id: str
    section_id: str
    units: Literal["µm"] = "µm"
    coordinate_note: str = Field(description="How x, y and z relate to the displayed section coordinates.")
    raw_file: str = Field(description="The deposited transcripts file the z values were read from.")
    raw_sha256: str
    molecules_sha256: str = Field(description="Checksum of the validated molecule table the sidecar is joined to.")
    sidecar_sha256: str
    molecules: int = Field(description="Validated molecules in the section.")
    with_depth: int
    missing_depth: int
    max_xy_disagreement_um: float = Field(description="Largest |x| or |y| difference between the raw row and the validated molecule.")
    z_min: float | None
    z_max: float | None


class DepthPoints(Contract):
    """Molecules inside a box (by their own x, y) with measured z, sampled deterministically to a point budget for
    drawing. Counts always say how many there are; the sample is for display only."""

    schema_version: str = SCHEMA_VERSION
    depth_version: str = DEPTH_VERSION
    section_id: str
    region: Region
    genes: list[str]
    z_range: list[float] = Field(description="[z0, z1] in µm, inclusive.")
    total_in_box: int = Field(description="Molecules of the genes in the box, with or without depth.")
    eligible: int = Field(description="Of those, with a measured z inside z_range.")
    displayed: int
    sampling: str
    x: list[float]
    y: list[float]
    z: list[float]
    gene_index: list[int] = Field(description="Index into `genes`.")
    assigned: list[bool] = Field(description="Counted toward a cell under the default condition.")
    kept_stricter: list[bool] = Field(description="Still counted under `stricter_condition`.")
    stricter_condition: str


class DepthBin(Contract):
    z0: float
    z1: float
    counts: dict[str, dict[str, int]] = Field(description="gene -> condition -> molecules in this interval.")


class DepthProfileRequest(Contract):
    region: Region
    genes: list[str] = Field(min_length=1)
    bin_um: float = Field(default=1.0, gt=0, le=20)
    cell_type: str | None = Field(default=None, description="Only molecules assigned (default condition) to cells of this type.")
    label_rule_id: str | None = None


class DepthProfile(Contract):
    """Full-data transcript counts of a box by depth interval, gene and assignment condition. Descriptive: it says
    where molecules sit in z, not why a signal is present."""

    schema_version: str = SCHEMA_VERSION
    depth_version: str = DEPTH_VERSION
    kind: Literal["new_descriptive_depth_exploration"] = "new_descriptive_depth_exploration"
    dataset_id: str
    section_id: str
    label_rule_id: str
    region: Region
    scope: str
    genes: list[str]
    cell_type: str | None
    conditions: list[str] = Field(description="'all' counts every molecule in scope; the others count molecules kept under that condition.")
    units: Literal["µm"] = "µm"
    bin_um: float
    bins: list[DepthBin]
    totals: dict[str, dict[str, int]] = Field(description="gene -> condition -> molecules over all bins; equals the sum of the bins.")
    missing_depth: dict[str, int] = Field(description="gene -> molecules in scope without a measured z (in no bin).")
    source: DepthSource
