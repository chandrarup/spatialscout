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
