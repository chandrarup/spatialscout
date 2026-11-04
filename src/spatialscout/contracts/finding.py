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
    """A region ranked by the result's ranking rule as showing the molecules behind it (rank 1 is first).
    `score` is the ranking count: the result's molecules in the population excluded under `condition`."""

    rank: int = Field(ge=1)
    region: Region
    score: float | None = None
    condition: ConditionName | None = None
    excluded_molecules: int | None = None
    default_molecules: int | None = Field(default=None, description="The result's molecules in the population in the window under the default condition.")


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
    cells_expressing: int | None = Field(
        default=None,
        description="Cells of the population that meet a presence measure under the condition (the observed value's "
        "numerator); null for the co-expression score.",
    )
    pairs_scored: int | None = Field(default=None, description="Co-expression score only: the marker pairs averaged.")


class AuditSectionValues(Contract):
    """One section of an audit result. `cells_labelled` is the fixed population count: cells carrying the
    label under the default condition. A cell without retained molecules stays in every denominator.
    `cells_with_retained_molecule` (per condition) counts population cells that keep at least one molecule of any
    gene, reported separately from the fixed denominator."""

    section_id: str
    cells_labelled: int
    conditions: list[AuditConditionValue]
    group: str | None = None
    eligible: bool | None = None
    ineligible_reason: str | None = None


class PooledConditionValue(Contract):
    """One condition pooled over the eligible sections, by the result's pooling rule (ratio of sums)."""

    condition: ConditionName
    cells: int
    molecules: int
    default_molecules: int
    retention: float | None
    observed_value: float | None
    expectation_cell_matched: float | None
    expectation_home_matched: float | None
    excess_drop_cell_matched: float | None
    excess_drop_home_matched: float | None
    below_home_threshold: bool | None = Field(
        default=None, description="Observed below the home-matched expectation times 2^-0.5 (an excess log2 drop above 0.5)."
    )
    missing_reasons: dict[str, str] = Field(default_factory=dict)


class LeaveOneSectionOutVerdict(Contract):
    """The audit verdict with one eligible section left out: which stricter conditions fall below the threshold."""

    left_out_section_id: str
    conditions_below_threshold: list[ConditionName]
    verdict: EvidenceStatus | None = Field(description="stable or segmentation_sensitive; null when an expectation is missing.")


class MarkerPairsSource(Contract):
    """The frozen exclusive-marker-pair artifact a result used, with the checksum of its file bytes."""

    path: str
    sha256: str
    frozen_on: str | None = None
    source_dataset: str | None = None
    source_url: str | None = None
    pair_count: int


class LeftOutSection(Contract):
    """A section of the dataset the result does not count, with the reason (for example a duplicate)."""

    section_id: str
    reason: str


class AuditRules(Contract):
    """The frozen analysis rules a result was computed under, recorded with it."""

    population_gate_min_cells: int
    molecule_gate_min_molecules: int
    min_eligible_sections: int
    excess_log2_drop_threshold: float
    home_label_rule_id: str
    home_cell_types: dict[str, str | None] = Field(description="Each gene's home cell type from the full-panel marker map; null when it has none.")
    result_molecules_rule: str
    pooling_rule: str
    label_rule: str
    expectation_rule: str


class AuditResult(Contract):
    schema_version: str = SCHEMA_VERSION
    finding_kind: Literal["audit"] = "audit"
    finding_id: str
    dataset_id: str
    population: Population
    genes: list[str] = Field(
        min_length=1, description="One gene, a gene set (presence of any), or every gene of the scored marker pairs."
    )
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
    gene_pairs: list[list[str]] = Field(default_factory=list, description="Co-expression score only: the marker pairs it averages.")
    marker_pairs: MarkerPairsSource | None = None
    pooled: list[PooledConditionValue] = Field(default_factory=list)
    leave_one_section_out: list[LeaveOneSectionOutVerdict] = Field(default_factory=list)
    eligible_by_group: dict[str, int] = Field(default_factory=dict)
    sections_left_out: list[LeftOutSection] = Field(default_factory=list)
    rules: AuditRules | None = None
    roi: Region | None = Field(
        default=None,
        description="The box the result is scoped to (a cell is inside when its centroid is, and brings all its "
        "molecules); null for a whole-section result.",
    )


class CompositeFigure(Contract):
    """An audit result's two-panel figure: A, per-section observed values against both expectations across
    conditions; B, a 300 x 300 µm crop around its top-ranked evidence region."""

    schema_version: str = SCHEMA_VERSION
    figure_id: str
    finding_id: str
    path: str = Field(description="PNG path relative to the dataset's artifact directory.")
    sha256: str
    crop: Region | None = Field(description="Panel B's crop; null when the result has no evidence region.")
    evidence_rank: int | None = None
    panel_a: str
    panel_b: str


class AuditIndexEntry(Contract):
    """One committed audit result, as the findings table lists it."""

    slug: str
    title: str
    finding_id: str
    finding_path: str
    label: EvidenceStatus
    label_rule_id: str
    cell_type: str
    genes: list[str]
    measure: str
    eligible_sections: int
    figure: CompositeFigure | None = None
    random_thinning_control_id: str | None = None
    random_thinning_control_path: str | None = None
    label_sensitivity_control_id: str | None = None
    label_sensitivity_control_path: str | None = None


class AuditIndex(Contract):
    """The committed audit results of a dataset, with the inputs they were computed from."""

    schema_version: str = SCHEMA_VERSION
    dataset_id: str
    generated_by: str
    sections_counted: list[str]
    sections_left_out: list[LeftOutSection]
    input_sha256: dict[str, str] = Field(description="sha256 of each input artifact, by path.")
    entries: list[AuditIndexEntry]
    section_disclosure: str | None = Field(default=None, description="How many sections and donors the dataset holds; shown with every section count.")


class GateStatus(Contract):
    """Cells and molecules in a box against the frozen gates, fast enough to show while a box is dragged."""

    section_id: str
    roi: Region | None
    cell_type: str
    genes: list[str]
    cells: int = Field(description="Cells of the population whose centroid lies in the box.")
    molecules: int = Field(description="Default-condition molecules of the genes assigned to those cells.")
    population_gate_min_cells: int
    molecule_gate_min_molecules: int
    passes_population_gate: bool
    passes_molecule_gate: bool
    status: str


class SectionLog2Value(Contract):
    """One section's library-size-normalised value, log2(CP10K + 1), under one condition."""

    section_id: str
    group: str
    condition: ConditionName
    library_size: int | None = None
    log2_value: float | None
    missing_reason: str | None = None
    gene_molecules: int | None = Field(default=None, description="Molecules of the gene in the population kept under the condition.")
    passes_molecule_gate: bool | None = None


class ConditionEffect(Contract):
    """The difference between group means of the log2 values under one condition (disease minus control)."""

    condition: ConditionName
    effect: float | None
    missing_reason: str | None = None
    disease_mean: float | None = None
    control_mean: float | None = None
    direction: Literal[-1, 0, 1] | None = Field(default=None, description="0 inside the near-zero band (±0.1 log2).")
    valid: bool | None = Field(default=None, description="Every section of both groups passes the molecule gate under the condition.")
    invalid_reason: str | None = None
    sections_used: list[str] = Field(default_factory=list)


class LeaveOneSectionOut(Contract):
    """The effect recomputed without one section, and whether its direction survives."""

    left_out_section_id: str
    condition: ConditionName
    effect: float | None
    direction_kept: bool | None
    direction: Literal[-1, 0, 1] | None = None


class ContrastSection(Contract):
    """One section of a contrast: its group and the fixed population count against the population gate."""

    section_id: str
    group: str
    cells_labelled: int
    passes_population_gate: bool


class ContrastRules(Contract):
    """The frozen contrast rules a result was computed under, recorded with it."""

    population_gate_min_cells: int
    molecule_gate_min_molecules: int
    near_zero_band_log2: float
    max_stable_range_log2: float
    label_rule_id: str
    normalisation: str
    value_rule: str
    effect_rule: str
    gate_precedence: str
    label_rule: str
    primary_conditions: list[ConditionName]
    exploratory_conditions: list[ConditionName] = Field(default_factory=list)


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
    donor_distinctness: str | None = Field(default=None, description="From the capability report, for example counts_do_not_reconcile.")
    sections: list[ContrastSection] = Field(default_factory=list)
    sections_left_out: list[LeftOutSection] = Field(default_factory=list)
    valid_conditions: list[ConditionName] = Field(default_factory=list)
    exploratory_per_section: list[SectionLog2Value] = Field(
        default_factory=list, description="The exploratory condition's values, on sections with structure masks only; never in the label (ADR-0006)."
    )
    evidence_regions: list[EvidenceRegion] = Field(default_factory=list)
    ranking_rule: str | None = None
    rules: ContrastRules | None = None
    section_disclosure: str | None = Field(default=None, description="How many sections and donors the dataset holds; shown with every section count.")


class ContrastIndexEntry(Contract):
    """One committed contrast result, as the findings table lists it."""

    slug: str
    title: str
    finding_id: str
    finding_path: str
    groups: Contrast
    label: EvidenceStatus
    label_rule_id: str
    cell_type: str
    gene: str
    disease_sections: int
    control_sections: int
    donor_distinctness: str | None = None
    figure: CompositeFigure | None = None


class ContrastRunConfiguration(Contract):
    """What a contrast batch ran: the frozen rules, conditions and the (cell type, gene) grid, fixed before computing."""

    rules: ContrastRules
    conditions: list[ConditionName]
    grid: list[list[str]] = Field(description="[label rule, cell type, gene] per result, per contrast.")
    contrasts: list[Contrast]


class ContrastIndex(Contract):
    """The committed contrast results of a dataset, with their run configuration and inputs."""

    schema_version: str = SCHEMA_VERSION
    dataset_id: str
    generated_by: str
    citation: str
    section_disclosure: str
    sections_counted: list[str]
    sections_left_out: list[LeftOutSection]
    input_sha256: dict[str, str]
    run_configuration: ContrastRunConfiguration
    entries: list[ContrastIndexEntry]


Finding = Annotated[AuditResult | ContrastResult, Field(discriminator="finding_kind")]
