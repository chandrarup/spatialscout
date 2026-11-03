"""Dataset contracts: provenance (manifest) and what the data supports (capability report)."""

from typing import Literal

from pydantic import Field

from .base import SCHEMA_VERSION, Contract


class CapabilityCheck(Contract):
    """One analysis and whether this dataset supports it, with the reason."""

    capability: str
    status: Literal["supported", "unavailable", "descriptive_only"]
    reason: str


class CapabilityReport(Contract):
    """For a dataset, which analyses are supported, unavailable or descriptive only, each with its reason."""

    schema_version: str = SCHEMA_VERSION
    dataset_id: str
    checks: list[CapabilityCheck]

    def supports(self, capability: str) -> bool:
        return any(c.capability == capability and c.status == "supported" for c in self.checks)


class SectionValidation(Contract):
    """What validation did to one section's raw records. Nothing is dropped silently: every molecule read is
    kept or counted under exactly one reason, in this order: malformed, duplicate, below quality, not in panel."""

    molecules_read: int
    malformed_molecules: int = Field(description="No gene, a non-finite position, quality or nucleus distance, or a nucleus flag other than 0 or 1.")
    duplicate_molecules: int = Field(description="A repeated transcript id; the first record is kept.")
    below_quality: int = Field(description="Quality score under the dataset's threshold.")
    not_in_panel: int = Field(description="A control probe or codeword, not a panel gene.")
    molecules_kept: int
    unassigned_molecules: int = Field(description="Kept molecules the instrument assigned to no cell.")
    unmatched_molecules: int = Field(
        description="Kept molecules assigned to a cell id missing from the cells table; kept, counted as unassigned."
    )
    cells_read: int
    malformed_cells: int = Field(description="No id, or a non-finite centroid or area.")
    duplicate_cells: int = Field(description="A repeated cell id; the first record is kept.")
    cells_kept: int
    cells_without_molecules: int = Field(description="Kept cells with no kept molecule; they stay in every denominator.")


class FileChecksum(Contract):
    path: str
    sha256: str
    bytes: int


class SectionInfo(Contract):
    section_id: str
    group: str
    extent: list[float] = Field(description="Bounding box in micrometres: x0, y0, x1, y1.")


class DatasetManifest(Contract):
    """Provenance of a dataset: where it came from, its files, panel and sections."""

    schema_version: str = SCHEMA_VERSION
    dataset_id: str
    title: str
    description: str
    synthetic: bool
    source_urls: list[str]
    download_date: str | None
    coordinate_units: str
    panel: list[str]
    sections: list[SectionInfo]
    files: list[FileChecksum]
    donor_caveat: str | None = None
