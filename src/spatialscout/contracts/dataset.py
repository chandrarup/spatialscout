"""Dataset contracts: provenance (manifest) and what the data supports (capability report)."""

from typing import Literal

from pydantic import Field

from .base import SCHEMA_VERSION, Contract, Contrast


class CapabilityCheck(Contract):
    """One analysis and whether this dataset supports it, with the reason."""

    capability: str
    status: Literal["supported", "unavailable", "descriptive_only"]
    reason: str


class ContrastEligibility(Contract):
    """Whether one contrast's groups support statistical inference. In this release every contrast is
    descriptive only, because GEO does not map sections to donors (ADR-0007). Donors are never inferred from
    expression."""

    groups: Contrast
    disease_section_ids: list[str]
    control_section_ids: list[str]
    disease_donors_published: int = Field(description="Donors in the disease group, from the paper's published counts.")
    control_donors_published: int = Field(description="Donors in the control group, from the paper's published counts.")
    donor_distinctness: Literal["repeat_donor_in_group", "conditionally_donor_distinct_unconfirmed", "counts_do_not_reconcile"]
    donor_distinctness_statement: str
    inference_eligibility: Literal["descriptive_only"] = "descriptive_only"
    inference_reason: str
    excluded_section_ids: list[str] = Field(
        default_factory=list, description="Sections of either group left out of the contrast, each named with its reason in inference_reason."
    )


class CapabilityReport(Contract):
    """For a dataset, which analyses are supported, unavailable or descriptive only, each with its reason."""

    schema_version: str = SCHEMA_VERSION
    dataset_id: str
    checks: list[CapabilityCheck]
    contrasts: list[ContrastEligibility] = Field(
        default_factory=list, description="The inference eligibility of every contrast the dataset allows."
    )

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
    malformed_cells: int = Field(description="No id, or a non-finite centroid or cell area.")
    duplicate_cells: int = Field(description="A repeated cell id; the first record is kept.")
    cells_kept: int
    cells_without_molecules: int = Field(description="Kept cells with no kept molecule; they stay in every denominator.")
    cells_without_nucleus: int = Field(default=0, description="Kept cells with no detected nucleus (empty nucleus_area).")


class LabelRule(Contract):
    """A frozen, named rule that assigns cell type labels from marker counts under the default condition."""

    label_rule_id: str
    description: str
    markers: dict[str, list[str]] = Field(description="Marker genes per cell type, in tie-break order.")
    ignored_genes: list[str] = Field(description="Genes the rule never reads when it decides membership.")
    score_threshold: float = Field(description="A cell's top marker score (count / gene scale) must reach this.")
    min_molecules: int = Field(description="A cell with fewer default molecules is labelled 'Low quality'.")


class LabelCounts(Contract):
    """One section's cells counted by cell type label under each rule, and the cells whose label differs."""

    cells: int
    cell_types: dict[str, dict[str, int]] = Field(description="Per label rule id, cells per cell type label.")
    differing_cells: int
    differing: dict[str, int] = Field(description="Cells per 'first-rule label -> second-rule label' change.")


class LabelRuleSet(Contract):
    """The frozen label rules of a dataset, the gene scales they use, and per-section label counts."""

    schema_version: str = SCHEMA_VERSION
    dataset_id: str
    rules: list[LabelRule]
    default_label_rule_id: str
    gene_scales: dict[str, float] = Field(
        description="Mean default molecules of each gene per expressing cell, pooled over the scale sections."
    )
    gene_scale_sections: list[str]
    sections: dict[str, LabelCounts]
    notes: list[str]
    citation: str


class FileChecksum(Contract):
    path: str
    sha256: str
    bytes: int


class SectionInfo(Contract):
    section_id: str
    group: str
    extent: list[float] = Field(description="Bounding box in micrometres: x0, y0, x1, y1.")
    name: str | None = Field(default=None, description="The section's name in its source, for example x2.")
    molecules: int | None = Field(default=None, description="Molecules in the validated table.")
    cells: int | None = Field(default=None, description="Cells in the validated table.")
    validation: SectionValidation | None = None
    content_sha256: str | None = Field(default=None, description="sha256 of the decompressed raw molecule and cell files.")
    duplicate_of: str | None = Field(
        default=None, description="An earlier section whose raw files hold identical content; analyses count only the earlier one."
    )


class DatasetFilters(Contract):
    """The quality and panel filters every validated molecule passed."""

    min_qv: float
    panel_genes_only: bool
    description: str


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
    filters: DatasetFilters | None = None
    label_rule_ids: list[str] = Field(default_factory=list, description="Frozen label rules; the first is the default.")
    citation: str | None = None
