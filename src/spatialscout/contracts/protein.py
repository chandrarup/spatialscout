"""Contracts for the KPMP CODEX protein-level audit (ticket 02c), the antibody-image analogue of an audit result."""

from pydantic import Field

from .base import Contract, EvidenceStatus
from .finding import Region


class ProteinThreshold(Contract):
    """A frozen positivity threshold on a marker's per-cell mean intensity."""

    marker: str
    value: float
    rule: str
    source_participant_id: str = Field(description="The participant whose cells the threshold was derived from.")


class ProteinConditionRow(Contract):
    """The result under one measurement condition. Population cells with no pixel kept count as not positive."""

    condition: str
    positive_cells: int = Field(description="Population cells whose mean of the marker under this condition is at or above its threshold.")
    observed_share: float | None
    expected_share: float | None = Field(description="Random-pixel-loss expectation: the mean over population cells of the probability that a random subset of the cell's pixels, as large as this condition keeps, has a mean at or above the threshold.")
    pixel_retention: float | None = Field(description="Population pixels kept under this condition / population pixels of the whole cells.")
    excluded_cells: int = Field(description="Population cells positive for the marker as whole cells but not under this condition.")
    retained_cells: int = Field(description="Population cells positive for the marker as whole cells and under this condition.")
    bordering_home_share_excluded: float | None = Field(description="Share of the excluded cells that border a home cell.")
    bordering_home_share_retained: float | None = Field(description="Share of the retained cells that border a home cell.")
    reasons: dict[str, str] = Field(default_factory=dict, description="Why a value is null.")


class ProteinAuditResult(Contract):
    """How the share of one marker's positive cells in a population behaves across measurement conditions, for one
    participant, over the whole image or a region. One participant against another is descriptive only."""

    result_id: str
    dataset_id: str
    participant_id: str
    role: str = Field(description="'healthy reference' or 'diseased'.")
    roi: Region | None
    population: str = Field(description="The population, frozen under the whole-cell condition, for example 'Podocalyxin+ cells'.")
    population_marker: str
    marker: str
    home: str = Field(description="The marker's home cells, for example 'LRP2+ cells that are not Podocalyxin+'.")
    population_cells: int
    home_cells: int
    thresholds: list[ProteinThreshold]
    conditions: list[ProteinConditionRow]
    label: EvidenceStatus
    label_reason: str
    inference: str
    rules: dict[str, str]
    cell_table_checksum: str = Field(description="sha256 of the per-cell table the result was computed from.")


class KpmpTile(Contract):
    """One display image of a channel: a horizontal strip of the participant's image, placed by its bounds (µm)."""

    path: str = Field(description="Under the artifacts directory; served at /api/kpmp/files/<path>.")
    bounds: Region


class KpmpChannel(Contract):
    channel_id: str
    marker: str
    label: str
    description: str
    display_max: float = Field(description="The raw intensity shown at full brightness.")
    tiles: list[KpmpTile]


class KpmpParticipant(Contract):
    participant_id: str
    panel_id: str
    role: str
    title: str
    extent: Region
    pixel_size_um: float
    cells: int
    mask_coverage: float = Field(description="Share of the image's pixels inside a segmentation label.")
    median_cell_area_um2: float
    mask_note: str
    channels: list[KpmpChannel]
    clinical: dict[str, str] = Field(description="Clinical values from downloaded KPMP files only; empty when none is downloaded.")
    clinical_note: str
    source_files: list[str]


class KpmpResultEntry(Contract):
    participant_id: str
    population_marker: str
    marker: str
    label: EvidenceStatus
    path: str


class KpmpManifest(Contract):
    dataset_id: str
    participants: list[KpmpParticipant]
    nucleus_threshold: ProteinThreshold
    thresholds: list[ProteinThreshold]
    results: list[KpmpResultEntry]
    display_rule: str
