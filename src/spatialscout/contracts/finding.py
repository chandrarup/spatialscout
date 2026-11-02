"""Finding contracts: a discriminated union on `finding_kind` (spec "Contracts").

- `audit`, an audit result: how a measure of one cell population (a gene's presence, a gene set's presence
  or a co-expression score) behaves across assignment conditions, per section, with its random-thinning
  expectations.
- `contrast`, a contrast result: a disease group against the control group for one gene in one cell type.
  Descriptive only in this release (ADR-0007).

Fields are typed but may start shallow: tickets 05 (audit) and 06 (contrast) fill them. A value the engine
does not compute yet stays null, with its reason in `missing_reasons`. The exploratory condition's values
are kept apart from the primary conditions and never enter a label (ADR-0006).
"""

from typing import Annotated, Literal

from pydantic import Field

from .base import SCHEMA_VERSION, ConditionName, Contract, Contrast, EvidenceStatus


class Region(Contract):
    """A rectangular window of a section, in micrometres, that the viewer shows and a claim can point to."""

    section_id: str
    x0: float
    y0: float
    x1: float
    y1: float


class EvidenceRegion(Contract):
    """A region ranked by the result's ranking rule as showing the molecules behind it (rank 1 is first)."""

    rank: int = Field(ge=1)
    region: Region
    score: float | None = None


class Population(Contract):
    """The cells a result is about: a cell type under a frozen label rule, fixed under the default condition."""

    label_rule_id: str
    cell_type: str


class AuditConditionValue(Contract):
    """One section under one assignment condition.

    `molecules` counts the result's molecules in the population kept under the condition; retention divides it
    by the default condition's count. Each excess drop is its expectation minus the observed value.
    """

    condition: ConditionName
    molecules: int
    retention: float | None
    observed_value: float | None
    nuclear_overlap_share: float | None
    cells_with_retained_molecule: int
    expectation_cell_matched: float | None = None
    expectation_home_matched: float | None = None
    excess_drop_cell_matched: float | None = None
    excess_drop_home_matched: float | None = None
    neighbour_proximity_share_excluded: float | None = None
    neighbour_proximity_share_retained: float | None = None
    missing_reasons: dict[str, str] = Field(default_factory=dict)


class AuditSectionValues(Contract):
    """One section of an audit result. `cells_labelled` is the fixed population count: cells carrying the
    label under the default condition. A cell without retained molecules stays in every denominator."""

    section_id: str
    cells_labelled: int
    conditions: list[AuditConditionValue]


class AuditResult(Contract):
    schema_version: str = SCHEMA_VERSION
    finding_kind: Literal["audit"] = "audit"
    finding_id: str
    dataset_id: str
    population: Population
    genes: list[str] = Field(min_length=1, max_length=2, description="One gene, or a gene pair for co-expression.")
    measure: Literal["share_expressing", "gene_set_share_expressing", "co_expression_score"]
    sections: list[AuditSectionValues]
    eligible_section_ids: list[str] = Field(
        description="Sections with at least 20 cells of the population and 10 of the result's molecules in them under "
        "the default condition; pooled values and the label use only these."
    )
    exploratory_sections: list[AuditSectionValues] = Field(default_factory=list)
    evidence_regions: list[EvidenceRegion] = Field(default_factory=list)
    ranking_rule: str | None = None
    label: EvidenceStatus
    label_reason: str
    source_artifact_ids: list[str] = Field(default_factory=list)


class SectionLog2Value(Contract):
    """One section's library-size-normalised value, log2(CP10K + 1), under one condition."""

    section_id: str
    group: str
    condition: ConditionName
    library_size: int | None = None
    log2_value: float | None
    missing_reason: str | None = None


class ConditionEffect(Contract):
    """The difference between group means of the log2 values under one condition."""

    condition: ConditionName
    effect: float | None
    missing_reason: str | None = None


class LeaveOneSectionOut(Contract):
    """The effect recomputed without one section, and whether its direction survives."""

    left_out_section_id: str
    condition: ConditionName
    effect: float | None
    direction_kept: bool | None


class ContrastResult(Contract):
    schema_version: str = SCHEMA_VERSION
    finding_kind: Literal["contrast"] = "contrast"
    finding_id: str
    dataset_id: str
    groups: Contrast
    population: Population
    gene: str
    per_section: list[SectionLog2Value]
    effects: list[ConditionEffect]
    leave_one_section_out: list[LeaveOneSectionOut]
    exploratory_effects: list[ConditionEffect] = Field(default_factory=list)
    inference_eligibility: Literal["descriptive_only"] = "descriptive_only"
    inference_reason: str
    label: EvidenceStatus
    label_reason: str
    source_artifact_ids: list[str] = Field(default_factory=list)


Finding = Annotated[AuditResult | ContrastResult, Field(discriminator="finding_kind")]
