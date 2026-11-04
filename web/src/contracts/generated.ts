/* Generated from the Pydantic contracts by `npm --prefix web run gen:types`. Do not edit by hand. */

/**
 * An assignment condition: a rule that decides which molecules count toward a cell (ADR-0002).
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ConditionName".
 */
export type ConditionName =
  "default" | "nucleus_only" | "distance_cap_1um" | "distance_cap_2um" | "structure_constrained";
/**
 * An evidence label. It says what the evidence supports, never whether a finding is biologically true.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "EvidenceStatus".
 */
export type EvidenceStatus = "stable" | "segmentation_sensitive" | "insufficient_evidence";
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "VerificationStatus".
 */
export type VerificationStatus = "pending" | "verified" | "failed" | "disputed" | "unavailable";
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ReviewStatus".
 */
export type ReviewStatus = "unreviewed" | "accepted_for_follow_up" | "needs_investigation" | "unresolved";
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "InjectedErrorKind".
 */
export type InjectedErrorKind =
  | "reversed_direction"
  | "wrong_section_count"
  | "wrong_dataset_reference"
  | "changed_effect"
  | "figure_label_mismatch"
  | "misstated_spatial_pattern"
  | "missing_required_control";
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "Finding".
 */
export type Finding = AuditResult | ContrastResult;
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "FindingKind".
 */
export type FindingKind = "audit" | "contrast";
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "InvestigationEvent".
 */
export type InvestigationEvent =
  | PlanProposedEvent
  | PlanApprovedEvent
  | PlanRejectedEvent
  | ToolStartedEvent
  | ToolFinishedEvent
  | ToolFailedEvent
  | AgentDecisionEvent
  | BudgetExhaustedEvent
  | ClaimDraftedEvent
  | ClaimRejectedEvent
  | ClaimVerifiedEvent
  | VerdictEvent
  | ReviewDecidedEvent
  | PackageReadyEvent
  | ModelCallEvent
  | ErrorEvent;
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "InvestigationStatus".
 */
export type InvestigationStatus = "planning" | "awaiting_approval" | "running" | "complete" | "failed" | "rejected";
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "RunMode".
 */
export type RunMode = "immutable_replay" | "cached_tool_rerun" | "live";

export interface SpatialScoutContracts {}
/**
 * Muse Spark 1.3 after reading one observation: what it read, the follow-ups it requested (each citing an
 * observation, with its status) and the questions it left open.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "AgentDecisionEvent".
 */
export interface AgentDecisionEvent {
  seq: number;
  investigation_id: string;
  recorded_at_utc: string;
  type: "agent_decision";
  observation_id: string;
  reading: string;
  requests: FollowUpRequest[];
  open_questions: string[];
  tool_calls_used: number;
  max_tool_calls: number;
}
/**
 * A follow-up request as the orchestrator recorded it: accepted (and run), rejected (with the reason) or over
 * budget (not run, and reported as an open question).
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "FollowUpRequest".
 */
export interface FollowUpRequest {
  /**
   * req-<n>, numbered in the order the agent made its requests.
   */
  request_id: string;
  tool: string;
  arguments: {
    [k: string]: unknown;
  };
  cites_observation_id: string;
  reason: string;
  status: "accepted" | "rejected" | "over_budget";
  rejection_reason: string | null;
}
/**
 * One section under one assignment condition.
 *
 * `molecules` counts the result's molecules in the population kept under the condition; retention divides it
 * by the default condition's count. Each excess drop is its expectation minus the observed value.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "AuditConditionValue".
 */
export interface AuditConditionValue {
  condition: ConditionName;
  molecules: number;
  retention: number | null;
  observed_value: number | null;
  nuclear_overlap_share: number | null;
  cells_with_retained_molecule: number;
  expectation_cell_matched: number | null;
  expectation_home_matched: number | null;
  excess_drop_cell_matched: number | null;
  excess_drop_home_matched: number | null;
  neighbour_proximity_share_excluded: number | null;
  neighbour_proximity_share_retained: number | null;
  missing_reasons: {
    [k: string]: string;
  };
  /**
   * Cells of the population that meet a presence measure under the condition (the observed value's numerator); null for the co-expression score.
   */
  cells_expressing: number | null;
  /**
   * Co-expression score only: the marker pairs averaged.
   */
  pairs_scored: number | null;
}
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "AuditEntry".
 */
export interface AuditEntry {
  schema_version: string;
  seq: number;
  investigation_id: string;
  recorded_at: string;
  kind:
    | "investigation_started"
    | "model_call"
    | "plan_proposed"
    | "plan_approved"
    | "plan_rejected"
    | "tool_call"
    | "tool_failed"
    | "agent_decision"
    | "budget_exhausted"
    | "claim_drafted"
    | "claim_rejected"
    | "claim_verified"
    | "claim_challenges_recorded"
    | "verdict_computed"
    | "review_decided"
    | "figure_failed"
    | "package_exported"
    | "error";
  payload: {
    [k: string]: unknown;
  };
  prev_hash: string;
  entry_hash: string;
}
/**
 * The committed audit results of a dataset, with the inputs they were computed from.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "AuditIndex".
 */
export interface AuditIndex {
  schema_version: string;
  dataset_id: string;
  generated_by: string;
  sections_counted: string[];
  sections_left_out: LeftOutSection[];
  /**
   * sha256 of each input artifact, by path.
   */
  input_sha256: {
    [k: string]: string;
  };
  entries: AuditIndexEntry[];
  /**
   * How many sections and donors the dataset holds; shown with every section count.
   */
  section_disclosure: string | null;
}
/**
 * A section of the dataset the result does not count, with the reason (for example a duplicate).
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "LeftOutSection".
 */
export interface LeftOutSection {
  section_id: string;
  reason: string;
}
/**
 * One committed audit result, as the findings table lists it.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "AuditIndexEntry".
 */
export interface AuditIndexEntry {
  slug: string;
  title: string;
  finding_id: string;
  finding_path: string;
  label: EvidenceStatus;
  label_rule_id: string;
  cell_type: string;
  genes: string[];
  measure: string;
  eligible_sections: number;
  figure: CompositeFigure | null;
  random_thinning_control_id: string | null;
  random_thinning_control_path: string | null;
  label_sensitivity_control_id: string | null;
  label_sensitivity_control_path: string | null;
}
/**
 * An audit result's two-panel figure: A, per-section observed values against both expectations across
 * conditions; B, a 300 x 300 µm crop around its top-ranked evidence region.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "CompositeFigure".
 */
export interface CompositeFigure {
  schema_version: string;
  figure_id: string;
  finding_id: string;
  /**
   * PNG path relative to the dataset's artifact directory.
   */
  path: string;
  sha256: string;
  /**
   * Panel B's crop; null when the result has no evidence region.
   */
  crop: Region | null;
  evidence_rank: number | null;
  panel_a: string;
  panel_b: string;
}
/**
 * A rectangular window of a section, in micrometres, that the viewer shows and a claim can point to.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "Region".
 */
export interface Region {
  section_id: string;
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}
/**
 * Retention and excluded molecules for one scope of a section under one assignment condition.
 *
 * A scope is the whole section (cell_type and gene are null), one cell type (gene is null), or one gene
 * within one cell type. Retention is the share of default-condition molecules the condition keeps; it is
 * null, with a reason, when the scope has no default-condition molecules.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "AuditMetrics".
 */
export interface AuditMetrics {
  section_id: string;
  condition: ConditionName;
  cell_type: string | null;
  gene: string | null;
  default_molecules: number;
  kept_molecules: number;
  excluded_molecules: number;
  retention: number | null;
  retention_missing_reason: string | null;
}
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "AuditResult".
 */
export interface AuditResult {
  schema_version: string;
  finding_kind: "audit";
  finding_id: string;
  dataset_id: string;
  population: Population;
  /**
   * One gene, a gene set (presence of any), or every gene of the scored marker pairs.
   *
   * @minItems 1
   */
  genes: [string, ...string[]];
  measure: "share_expressing" | "gene_set_share_expressing" | "co_expression_score";
  sections: AuditSectionValues[];
  /**
   * Sections with at least 20 cells of the population and 10 of the result's molecules in them under the default condition; pooled values and the label use only these.
   */
  eligible_section_ids: string[];
  exploratory_sections: AuditSectionValues[];
  evidence_regions: EvidenceRegion[];
  ranking_rule: string | null;
  label: EvidenceStatus;
  label_reason: string;
  source_artifact_ids: string[];
  /**
   * Co-expression score only: the marker pairs it averages.
   */
  gene_pairs: string[][];
  marker_pairs: MarkerPairsSource | null;
  pooled: PooledConditionValue[];
  leave_one_section_out: LeaveOneSectionOutVerdict[];
  eligible_by_group: {
    [k: string]: number;
  };
  sections_left_out: LeftOutSection[];
  rules: AuditRules | null;
  /**
   * The box the result is scoped to (a cell is inside when its centroid is, and brings all its molecules); null for a whole-section result.
   */
  roi: Region | null;
}
/**
 * The cells a result is about: a cell type under a frozen label rule, fixed under the default condition.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "Population".
 */
export interface Population {
  label_rule_id: string;
  cell_type: string;
}
/**
 * One section of an audit result. `cells_labelled` is the fixed population count: cells carrying the
 * label under the default condition. A cell without retained molecules stays in every denominator.
 * `cells_with_retained_molecule` (per condition) counts population cells that keep at least one molecule of any
 * gene, reported separately from the fixed denominator.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "AuditSectionValues".
 */
export interface AuditSectionValues {
  section_id: string;
  cells_labelled: number;
  conditions: AuditConditionValue[];
  group: string | null;
  eligible: boolean | null;
  ineligible_reason: string | null;
}
/**
 * A region ranked by the result's ranking rule as showing the molecules behind it (rank 1 is first).
 * `score` is the ranking count: the result's molecules in the population excluded under `condition`.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "EvidenceRegion".
 */
export interface EvidenceRegion {
  rank: number;
  region: Region;
  score: number | null;
  condition: ConditionName | null;
  excluded_molecules: number | null;
  /**
   * The result's molecules in the population in the window under the default condition.
   */
  default_molecules: number | null;
}
/**
 * The frozen exclusive-marker-pair artifact a result used, with the checksum of its file bytes.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "MarkerPairsSource".
 */
export interface MarkerPairsSource {
  path: string;
  sha256: string;
  frozen_on: string | null;
  source_dataset: string | null;
  source_url: string | null;
  pair_count: number;
}
/**
 * One condition pooled over the eligible sections, by the result's pooling rule (ratio of sums).
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "PooledConditionValue".
 */
export interface PooledConditionValue {
  condition: ConditionName;
  cells: number;
  molecules: number;
  default_molecules: number;
  retention: number | null;
  observed_value: number | null;
  expectation_cell_matched: number | null;
  expectation_home_matched: number | null;
  excess_drop_cell_matched: number | null;
  excess_drop_home_matched: number | null;
  /**
   * Observed below the home-matched expectation times 2^-0.5 (an excess log2 drop above 0.5).
   */
  below_home_threshold: boolean | null;
  missing_reasons: {
    [k: string]: string;
  };
}
/**
 * The audit verdict with one eligible section left out: which stricter conditions fall below the threshold.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "LeaveOneSectionOutVerdict".
 */
export interface LeaveOneSectionOutVerdict {
  left_out_section_id: string;
  conditions_below_threshold: ConditionName[];
  /**
   * stable or segmentation_sensitive; null when an expectation is missing.
   */
  verdict: EvidenceStatus | null;
}
/**
 * The frozen analysis rules a result was computed under, recorded with it.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "AuditRules".
 */
export interface AuditRules {
  population_gate_min_cells: number;
  molecule_gate_min_molecules: number;
  min_eligible_sections: number;
  excess_log2_drop_threshold: number;
  home_label_rule_id: string;
  /**
   * Each gene's home cell type from the full-panel marker map; null when it has none.
   */
  home_cell_types: {
    [k: string]: string | null;
  };
  result_molecules_rule: string;
  pooling_rule: string;
  label_rule: string;
  expectation_rule: string;
}
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "Budget".
 */
export interface Budget {
  max_tool_calls: number;
}
/**
 * The plan's tool-call budget is spent: the investigation drafts claims from the evidence it has and reports
 * what it could not settle.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "BudgetExhaustedEvent".
 */
export interface BudgetExhaustedEvent {
  seq: number;
  investigation_id: string;
  recorded_at_utc: string;
  type: "budget_exhausted";
  tool_calls_used: number;
  max_tool_calls: number;
  open_questions: OpenQuestion[];
}
/**
 * Something the investigation could not settle: a follow-up the budget did not allow, an observation the agent
 * never read because the budget ran out, or a question the agent raised.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "OpenQuestion".
 */
export interface OpenQuestion {
  text: string;
  source: "over_budget_request" | "unread_observation" | "agent";
  observation_id: string | null;
  request_id: string | null;
}
/**
 * A computed input a model request was built from. Part of the cache key, so a changed tool version
 * or artifact invalidates the stored response.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "CacheInput".
 */
export interface CacheInput {
  name: string;
  version: string;
  sha256: string;
}
/**
 * One analysis and whether this dataset supports it, with the reason.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "CapabilityCheck".
 */
export interface CapabilityCheck {
  capability: string;
  status: "supported" | "unavailable" | "descriptive_only";
  reason: string;
}
/**
 * For a dataset, which analyses are supported, unavailable or descriptive only, each with its reason.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "CapabilityReport".
 */
export interface CapabilityReport {
  schema_version: string;
  dataset_id: string;
  checks: CapabilityCheck[];
  /**
   * The inference eligibility of every contrast the dataset allows.
   */
  contrasts: ContrastEligibility[];
}
/**
 * Whether one contrast's groups support statistical inference. In this release every contrast is
 * descriptive only, because GEO does not map sections to donors (ADR-0007). Donors are never inferred from
 * expression.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ContrastEligibility".
 */
export interface ContrastEligibility {
  groups: Contrast;
  disease_section_ids: string[];
  control_section_ids: string[];
  /**
   * Donors in the disease group, from the paper's published counts.
   */
  disease_donors_published: number;
  /**
   * Donors in the control group, from the paper's published counts.
   */
  control_donors_published: number;
  donor_distinctness: "repeat_donor_in_group" | "conditionally_donor_distinct_unconfirmed" | "counts_do_not_reconcile";
  donor_distinctness_statement: string;
  inference_eligibility: "descriptive_only";
  inference_reason: string;
  /**
   * Sections of either group left out of the contrast, each named with its reason in inference_reason.
   */
  excluded_section_ids: string[];
}
/**
 * One disease group compared with the control group, for example DKD vs Control.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "Contrast".
 */
export interface Contrast {
  disease: string;
  control: string;
}
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "CellColumns".
 */
export interface CellColumns {
  cell_id: string[];
  x: number[];
  y: number[];
  /**
   * Radius of a circle with the nucleus's area: an approximation.
   */
  nucleus_radius: number[];
  /**
   * Index into RegionView.cell_types.
   */
  cell_type_index: number[];
}
/**
 * The outcome of checking an audit log's hash chain. `first_bad_seq` is the first entry that fails.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ChainCheckResult".
 */
export interface ChainCheckResult {
  ok: boolean;
  entries: number;
  head_hash: string | null;
  first_bad_seq: number | null;
  reason: string | null;
}
/**
 * Every rendered channel of one section, in a fixed order.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ChannelSet".
 */
export interface ChannelSet {
  schema_version: string;
  dataset_id: string;
  section_id: string;
  provenance: "rendered from molecules";
  channels: RenderedChannel[];
}
/**
 * One channel of a section: which molecules (or nuclei) it draws, and whether the section has any.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "RenderedChannel".
 */
export interface RenderedChannel {
  channel_id: string;
  label: string;
  source: "molecules" | "nuclei";
  /**
   * The genes whose molecules the channel draws; empty for the nuclei channel.
   */
  genes: string[];
  description: string;
  /**
   * Molecules of the channel's genes in the section, assigned or not; for nuclei, cells with a detected nucleus.
   */
  count: number;
  available: boolean;
  /**
   * The channel's genes with no molecule in the section.
   */
  missing_genes: string[];
  unavailable_reason: string | null;
}
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ChatMessage".
 */
export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "CheckResult".
 */
export interface CheckResult {
  kind: "structural" | "numerical" | "visual";
  status: "passed" | "failed" | "disputed" | "unavailable";
  details: string;
  /**
   * Every problem the check found; empty when it passed.
   */
  reasons: string[];
}
/**
 * One number the claim's text uses, and the field of the cited finding it comes from.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "CitedNumber".
 */
export interface CitedNumber {
  value: number | null;
  source: string;
}
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "Claim".
 */
export interface Claim {
  schema_version: string;
  claim_id: string;
  version: number;
  investigation_id: string;
  dataset_id: string;
  finding: FindingRef;
  text: string;
  cited: {
    [k: string]: CitedNumber;
  };
  controls: ClaimControls;
  figure_id: string | null;
  evidence_status: EvidenceStatus;
  verification_status: VerificationStatus;
  review_status: ReviewStatus;
  injected: InjectedError;
  /**
   * The direction the claim states, when it states one in structured form; else read from its text.
   */
  direction: ("holds" | "drops") | null;
  /**
   * The neighbour pattern the claim states, if any.
   */
  neighbour_pattern: ("excluded_nearer_home" | "excluded_not_nearer_home") | null;
}
/**
 * The one finding a claim cites.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "FindingRef".
 */
export interface FindingRef {
  finding_id: string;
  finding_kind: "audit" | "contrast";
}
/**
 * Ids of the controls the claim cites; a required control that is missing fails verification.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ClaimControls".
 */
export interface ClaimControls {
  random_thinning: string | null;
  label_sensitivity: string | null;
}
/**
 * Whether this claim is a deliberately altered copy used to test verification. Always shown when true.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "InjectedError".
 */
export interface InjectedError {
  is_injected: boolean;
  kind: InjectedErrorKind | null;
}
/**
 * One recorded injected variant of a claim and its recorded verification. `detected` is the recorded outcome:
 * true when a check found a problem the original claim did not have (`new_reasons`), false for a miss.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ClaimChallenge".
 */
export interface ClaimChallenge {
  kind: InjectedErrorKind;
  claim: Claim;
  verification: VerificationResult;
  changes: FieldChange[];
  new_reasons: string[];
  detected: boolean;
}
/**
 * Every check run on one claim version, and the verification status they add up to.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "VerificationResult".
 */
export interface VerificationResult {
  schema_version: string;
  claim_id: string;
  claim_version: number;
  checks: CheckResult[];
  verification_status: VerificationStatus;
  finding_id: string | null;
  /**
   * The composite figure the visual check read.
   */
  figure: CompositeFigure | null;
  visual: VisualAnswer | null;
  /**
   * The declared tolerances of the numerical check.
   */
  tolerances: {
    [k: string]: number;
  };
  /**
   * Each cited source's independently recomputed value.
   */
  recomputed: {
    [k: string]: unknown;
  };
  /**
   * False for a failed claim: it stays in history only.
   */
  in_validated_summary: boolean;
}
/**
 * Muse Spark 1.3's reading of a composite figure, against this schema. A consistency check, not ground truth.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "VisualAnswer".
 */
export interface VisualAnswer {
  /**
   * What Panel A shows: holds when the pooled observed line stays at or above the threshold line under every stricter condition, drops when it falls below it under at least one.
   */
  panel_a_direction: "holds" | "drops" | "unclear";
  /**
   * Panel A's direction is the direction the claim states.
   */
  panel_a_matches_claim: boolean;
  /**
   * One section's line alone accounts for Panel A's pooled direction.
   */
  single_section_drives_panel_a: boolean;
  /**
   * Panel B, read with the computed neighbour-proximity shares, shows the neighbour pattern the claim states; null when the claim states none.
   */
  panel_b_matches_claim: boolean | null;
  /**
   * One or two sentences on what the panels show.
   */
  explanation: string;
}
/**
 * One field an injected error changed.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "FieldChange".
 */
export interface FieldChange {
  field: string;
  before: unknown;
  after: unknown;
}
/**
 * The "Challenge the verifier" options of one claim: its injected variants, named only by error kind.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ClaimChallenges".
 */
export interface ClaimChallenges {
  schema_version: string;
  claim_id: string;
  claim_version: number;
  base_status: VerificationStatus;
  variants: ClaimChallenge[];
}
/**
 * The claim-drafting model's structured output: the sentence and every number it uses.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ClaimDraft".
 */
export interface ClaimDraft {
  text: string;
  cited: {
    [k: string]: CitedNumber;
  };
}
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ClaimDraftedEvent".
 */
export interface ClaimDraftedEvent {
  seq: number;
  investigation_id: string;
  recorded_at_utc: string;
  type: "claim_drafted";
  claim: Claim;
}
/**
 * A claim draft that failed validation even after one redraft. No claim is made from it.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ClaimRejectedEvent".
 */
export interface ClaimRejectedEvent {
  seq: number;
  investigation_id: string;
  recorded_at_utc: string;
  type: "claim_rejected";
  finding_id: string;
  problems: string[];
}
/**
 * A claim version after its three checks, with its verification status and every reason. An injected variant
 * carries `claim.injected.is_injected` and is always shown as injected.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ClaimVerifiedEvent".
 */
export interface ClaimVerifiedEvent {
  seq: number;
  investigation_id: string;
  recorded_at_utc: string;
  type: "claim_verified";
  claim: Claim;
  verification: VerificationResult;
}
/**
 * The difference between group means of the log2 values under one condition (disease minus control).
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ConditionEffect".
 */
export interface ConditionEffect {
  condition: ConditionName;
  effect: number | null;
  missing_reason: string | null;
  disease_mean: number | null;
  control_mean: number | null;
  /**
   * 0 inside the near-zero band (±0.1 log2).
   */
  direction: (-1 | 0 | 1) | null;
  /**
   * Every section of both groups passes the molecule gate under the condition.
   */
  valid: boolean | null;
  invalid_reason: string | null;
  sections_used: string[];
}
/**
 * The committed contrast results of a dataset, with their run configuration and inputs.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ContrastIndex".
 */
export interface ContrastIndex {
  schema_version: string;
  dataset_id: string;
  generated_by: string;
  citation: string;
  section_disclosure: string;
  sections_counted: string[];
  sections_left_out: LeftOutSection[];
  input_sha256: {
    [k: string]: string;
  };
  run_configuration: ContrastRunConfiguration;
  entries: ContrastIndexEntry[];
}
/**
 * What a contrast batch ran: the frozen rules, conditions and the (cell type, gene) grid, fixed before computing.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ContrastRunConfiguration".
 */
export interface ContrastRunConfiguration {
  rules: ContrastRules;
  conditions: ConditionName[];
  /**
   * [label rule, cell type, gene] per result, per contrast.
   */
  grid: string[][];
  contrasts: Contrast[];
}
/**
 * The frozen contrast rules a result was computed under, recorded with it.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ContrastRules".
 */
export interface ContrastRules {
  population_gate_min_cells: number;
  molecule_gate_min_molecules: number;
  near_zero_band_log2: number;
  max_stable_range_log2: number;
  label_rule_id: string;
  normalisation: string;
  value_rule: string;
  effect_rule: string;
  gate_precedence: string;
  label_rule: string;
  primary_conditions: ConditionName[];
  exploratory_conditions: ConditionName[];
}
/**
 * One committed contrast result, as the findings table lists it.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ContrastIndexEntry".
 */
export interface ContrastIndexEntry {
  slug: string;
  title: string;
  finding_id: string;
  finding_path: string;
  groups: Contrast;
  label: EvidenceStatus;
  label_rule_id: string;
  cell_type: string;
  gene: string;
  disease_sections: number;
  control_sections: number;
  donor_distinctness: string | null;
  figure: CompositeFigure | null;
}
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ContrastResult".
 */
export interface ContrastResult {
  schema_version: string;
  finding_kind: "contrast";
  finding_id: string;
  dataset_id: string;
  groups: Contrast;
  population: Population;
  gene: string;
  per_section: SectionLog2Value[];
  effects: ConditionEffect[];
  leave_one_section_out: LeaveOneSectionOut[];
  exploratory_effects: ConditionEffect[];
  inference_eligibility: "descriptive_only";
  inference_reason: string;
  label: EvidenceStatus;
  label_reason: string;
  source_artifact_ids: string[];
  /**
   * From the capability report, for example counts_do_not_reconcile.
   */
  donor_distinctness: string | null;
  sections: ContrastSection[];
  sections_left_out: LeftOutSection[];
  valid_conditions: ConditionName[];
  /**
   * The exploratory condition's values, on sections with structure masks only; never in the label (ADR-0006).
   */
  exploratory_per_section: SectionLog2Value[];
  evidence_regions: EvidenceRegion[];
  ranking_rule: string | null;
  rules: ContrastRules | null;
  /**
   * How many sections and donors the dataset holds; shown with every section count.
   */
  section_disclosure: string | null;
}
/**
 * One section's library-size-normalised value, log2(CP10K + 1), under one condition.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "SectionLog2Value".
 */
export interface SectionLog2Value {
  section_id: string;
  group: string;
  condition: ConditionName;
  library_size: number | null;
  log2_value: number | null;
  missing_reason: string | null;
  /**
   * Molecules of the gene in the population kept under the condition.
   */
  gene_molecules: number | null;
  passes_molecule_gate: boolean | null;
}
/**
 * The effect recomputed without one section, and whether its direction survives.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "LeaveOneSectionOut".
 */
export interface LeaveOneSectionOut {
  left_out_section_id: string;
  condition: ConditionName;
  effect: number | null;
  direction_kept: boolean | null;
  direction: (-1 | 0 | 1) | null;
}
/**
 * One section of a contrast: its group and the fixed population count against the population gate.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ContrastSection".
 */
export interface ContrastSection {
  section_id: string;
  group: string;
  cells_labelled: number;
  passes_population_gate: boolean;
}
/**
 * The quality and panel filters every validated molecule passed.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "DatasetFilters".
 */
export interface DatasetFilters {
  min_qv: number;
  panel_genes_only: boolean;
  description: string;
}
/**
 * Provenance of a dataset: where it came from, its files, panel and sections.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "DatasetManifest".
 */
export interface DatasetManifest {
  schema_version: string;
  dataset_id: string;
  title: string;
  description: string;
  synthetic: boolean;
  source_urls: string[];
  download_date: string | null;
  coordinate_units: string;
  panel: string[];
  sections: SectionInfo[];
  files: FileChecksum[];
  donor_caveat: string | null;
  filters: DatasetFilters | null;
  /**
   * Frozen label rules; the first is the default.
   */
  label_rule_ids: string[];
  citation: string | null;
}
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "SectionInfo".
 */
export interface SectionInfo {
  section_id: string;
  group: string;
  /**
   * Bounding box in micrometres: x0, y0, x1, y1.
   */
  extent: number[];
  /**
   * The section's name in its source, for example x2.
   */
  name: string | null;
  /**
   * Molecules in the validated table.
   */
  molecules: number | null;
  /**
   * Cells in the validated table.
   */
  cells: number | null;
  validation: SectionValidation | null;
  /**
   * sha256 of the decompressed raw molecule and cell files.
   */
  content_sha256: string | null;
  /**
   * An earlier section whose raw files hold identical content; analyses count only the earlier one.
   */
  duplicate_of: string | null;
}
/**
 * What validation did to one section's raw records. Nothing is dropped silently: every molecule read is
 * kept or counted under exactly one reason, in this order: malformed, duplicate, below quality, not in panel.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "SectionValidation".
 */
export interface SectionValidation {
  molecules_read: number;
  /**
   * No gene, a non-finite position, quality or nucleus distance, or a nucleus flag other than 0 or 1.
   */
  malformed_molecules: number;
  /**
   * A repeated transcript id; the first record is kept.
   */
  duplicate_molecules: number;
  /**
   * Quality score under the dataset's threshold.
   */
  below_quality: number;
  /**
   * A control probe or codeword, not a panel gene.
   */
  not_in_panel: number;
  molecules_kept: number;
  /**
   * Kept molecules the instrument assigned to no cell.
   */
  unassigned_molecules: number;
  /**
   * Kept molecules assigned to a cell id missing from the cells table; kept, counted as unassigned.
   */
  unmatched_molecules: number;
  cells_read: number;
  /**
   * No id, or a non-finite centroid or cell area.
   */
  malformed_cells: number;
  /**
   * A repeated cell id; the first record is kept.
   */
  duplicate_cells: number;
  cells_kept: number;
  /**
   * Kept cells with no kept molecule; they stay in every denominator.
   */
  cells_without_molecules: number;
  /**
   * Kept cells with no detected nucleus (empty nucleus_area).
   */
  cells_without_nucleus: number;
}
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "FileChecksum".
 */
export interface FileChecksum {
  path: string;
  sha256: string;
  bytes: number;
}
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ErrorEvent".
 */
export interface ErrorEvent {
  seq: number;
  investigation_id: string;
  recorded_at_utc: string;
  type: "error";
  code: string;
  message: string;
}
/**
 * Fields every event carries. `seq` starts at 1 and increases by one per event within an
 * investigation; `recorded_at_utc` is when the event was first recorded and never changes on replay.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "EventBase".
 */
export interface EventBase {
  seq: number;
  investigation_id: string;
  recorded_at_utc: string;
}
/**
 * The agent model's structured output after reading one observation.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "FollowUpDecision".
 */
export interface FollowUpDecision {
  /**
   * What the agent reads in the observation, in one to three sentences.
   */
  reading: string;
  /**
   * Follow-up tool calls; empty when the observation needs none.
   */
  requests: FollowUpProposal[];
  /**
   * Questions the evidence leaves open that the registry's tools cannot answer.
   */
  open_questions: string[];
}
/**
 * One follow-up tool call as the agent model proposes it, before it is checked against the registry.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "FollowUpProposal".
 */
export interface FollowUpProposal {
  tool: string;
  arguments: {
    [k: string]: unknown;
  };
  /**
   * The id of the observation that prompted this request, such as obs-1.
   */
  cites_observation: string;
  /**
   * Why this observation calls for this tool, in one or two sentences.
   */
  reason: string;
}
/**
 * Cells and molecules in a box against the frozen gates, fast enough to show while a box is dragged.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "GateStatus".
 */
export interface GateStatus {
  section_id: string;
  roi: Region | null;
  cell_type: string;
  genes: string[];
  /**
   * Cells of the population whose centroid lies in the box.
   */
  cells: number;
  /**
   * Default-condition molecules of the genes assigned to those cells.
   */
  molecules: number;
  population_gate_min_cells: number;
  molecule_gate_min_molecules: number;
  passes_population_gate: boolean;
  passes_molecule_gate: boolean;
  status: string;
}
/**
 * Every sub-claim's verdict, in the investigation's sections and under the controls its claims cite.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "HypothesisVerdict".
 */
export interface HypothesisVerdict {
  question: string;
  scope: string;
  verdicts: SubClaimVerdict[];
  rule: string;
}
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "SubClaimVerdict".
 */
export interface SubClaimVerdict {
  sub_claim: SubClaim;
  verdict: "confirmed" | "refuted" | "inconclusive";
  reason: string;
  /**
   * The verified claim versions the verdict rests on.
   */
  claim_ids: string[];
  dataset_id: string;
}
/**
 * One testable part of the question: a population, its genes, and what the hypothesis predicts under stricter
 * assignment conditions. A prediction, never an outcome.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "SubClaim".
 */
export interface SubClaim {
  /**
   * The sub-claim as a question-scoped statement, for example 'podocyte LRP2/CUBN presence persists'.
   */
  text: string;
  /**
   * A cell type label from the dataset's label rules.
   */
  cell_type: string;
  /**
   * Panel genes the sub-claim is about.
   */
  genes: string[];
  /**
   * What the researcher's hypothesis predicts: 'holds' (the signal stays when assignment is stricter, as real cell content would) or 'drops' (it falls beyond random thinning, as admixture from neighbours would).
   */
  predicted: "holds" | "drops";
}
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "PlanProposedEvent".
 */
export interface PlanProposedEvent {
  seq: number;
  investigation_id: string;
  recorded_at_utc: string;
  type: "plan_proposed";
  plan: Plan;
}
/**
 * The ordered tool steps proposed for a question; frozen once approved (its hash is then recorded).
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "Plan".
 */
export interface Plan {
  schema_version: string;
  plan_id: string;
  investigation_id: string;
  question: string;
  dataset_id: string;
  summary: string;
  contrast: Contrast | null;
  cell_types: string[];
  conditions: ConditionName[];
  steps: PlanStep[];
  sub_claims: SubClaim[];
  budget: Budget;
  proposed_by: string;
  status: "proposed" | "approved" | "rejected";
  approved_at_utc: string | null;
  /**
   * sha256 of the proposed plan's canonical JSON, set at approval.
   */
  plan_hash: string | null;
}
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "PlanStep".
 */
export interface PlanStep {
  step_id: string;
  tool: string;
  arguments: {
    [k: string]: unknown;
  };
  rationale: string;
}
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "PlanApprovedEvent".
 */
export interface PlanApprovedEvent {
  seq: number;
  investigation_id: string;
  recorded_at_utc: string;
  type: "plan_approved";
  plan_id: string;
  plan_hash: string;
}
/**
 * A plan turned down. By the validator: it names a tool outside the registry, invalid arguments or an analysis
 * the capability report does not support; the planner gets one re-plan. By the researcher: the investigation ends
 * and nothing runs.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "PlanRejectedEvent".
 */
export interface PlanRejectedEvent {
  seq: number;
  investigation_id: string;
  recorded_at_utc: string;
  type: "plan_rejected";
  by: "validator" | "researcher";
  /**
   * 1 for the first proposal, 2 for the re-plan.
   */
  attempt: number;
  reason: string;
  /**
   * The tools the rejected proposal named.
   */
  tools: string[];
  plan_id: string | null;
}
/**
 * A tool call starting. A plan step has no request; a follow-up names its request and the observation it cites.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ToolStartedEvent".
 */
export interface ToolStartedEvent {
  seq: number;
  investigation_id: string;
  recorded_at_utc: string;
  type: "tool_started";
  step_id: string;
  tool: string;
  arguments: {
    [k: string]: unknown;
  };
  /**
   * The observation this call will produce.
   */
  observation_id: string | null;
  request_id: string | null;
  cites_observation_id: string | null;
  /**
   * A plan step's rationale, or the agent's reason for a follow-up.
   */
  reason: string | null;
}
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ToolFinishedEvent".
 */
export interface ToolFinishedEvent {
  seq: number;
  investigation_id: string;
  recorded_at_utc: string;
  type: "tool_finished";
  step_id: string;
  tool: string;
  artifact_id: string;
  summary: string;
  observation_id: string | null;
  /**
   * The artifact's computed evidence label, when it has one.
   */
  label: EvidenceStatus | null;
}
/**
 * A tool call that raised instead of returning an artifact. The failure is itself an observation the agent reads.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ToolFailedEvent".
 */
export interface ToolFailedEvent {
  seq: number;
  investigation_id: string;
  recorded_at_utc: string;
  type: "tool_failed";
  step_id: string;
  tool: string;
  observation_id: string;
  error: string;
}
/**
 * Each sub-claim's verdict, derived by the frozen rule from the verified claims once verification ends.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "VerdictEvent".
 */
export interface VerdictEvent {
  seq: number;
  investigation_id: string;
  recorded_at_utc: string;
  type: "verdict";
  verdict: HypothesisVerdict;
}
/**
 * The researcher's decision on one claim version, and the claim with its new review status.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ReviewDecidedEvent".
 */
export interface ReviewDecidedEvent {
  seq: number;
  investigation_id: string;
  recorded_at_utc: string;
  type: "review_decided";
  decision: ReviewDecision;
  claim: Claim;
}
/**
 * The researcher's decision on one claim version; voice decisions need confirmation.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ReviewDecision".
 */
export interface ReviewDecision {
  schema_version: string;
  decision_id: string;
  claim_id: string;
  claim_version: number;
  decision: "accepted_for_follow_up" | "needs_investigation" | "unresolved";
  reviewer: string;
  decided_at_utc: string;
  via: "click" | "voice";
  confirmed: boolean;
}
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "PackageReadyEvent".
 */
export interface PackageReadyEvent {
  seq: number;
  investigation_id: string;
  recorded_at_utc: string;
  type: "package_ready";
  package: PackageInfo;
}
/**
 * What the UI needs to offer an evidence package for download.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "PackageInfo".
 */
export interface PackageInfo {
  package_id: string;
  download_url: string;
  created_at: string;
  files: string[];
  audit_log: ChainCheckResult;
  review_state: "work_in_progress" | "reviewed";
  open_questions: OpenQuestion[];
}
/**
 * Telemetry for one model call: provider, model, purpose, latency, tokens, estimated cost, whether the
 * response was live or stored, and the run mode. Never carries keys or prompt text.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ModelCallEvent".
 */
export interface ModelCallEvent {
  seq: number;
  investigation_id: string;
  recorded_at_utc: string;
  type: "model_call";
  call: ModelCallRecord;
}
/**
 * One model call as the audit log records it and the telemetry pills show it, including whether its
 * response was live (`source: live`) or stored (`source: replay`).
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ModelCallRecord".
 */
export interface ModelCallRecord {
  call_id: string;
  purpose: string;
  provider: "meta" | "baseten" | "fireworks";
  model: string;
  cache_key: string;
  source: "live" | "replay" | "cache";
  recording_id: string | null;
  started_at: string;
  latency_ms: number;
  finish_reason: string;
  usage: TokenUsage | null;
  /**
   * Spend charged to the live budget; null for stored responses.
   */
  estimated_cost_usd: number | null;
  run_mode: ("immutable_replay" | "cached_tool_rerun" | "live") | null;
  /**
   * The provider that answered; differs from `provider` after failover.
   */
  served_by: ("meta" | "baseten" | "fireworks") | null;
  failover_from: ("meta" | "baseten" | "fireworks") | null;
  /**
   * Set when the call produced no usable response.
   */
  error_code: string | null;
}
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "TokenUsage".
 */
export interface TokenUsage {
  prompt_tokens: number | null;
  completion_tokens: number | null;
  reasoning_tokens: number | null;
}
/**
 * The current state of one investigation, including every event emitted so far.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "InvestigationSnapshot".
 */
export interface InvestigationSnapshot {
  investigation_id: string;
  question: string;
  status: InvestigationStatus;
  run_mode: "immutable_replay" | "cached_tool_rerun" | "live";
  replay: ReplayInfo | null;
  dataset_id: string;
  plan: Plan | null;
  claims: Claim[];
  package: PackageInfo | null;
  events: (
    | PlanProposedEvent
    | PlanApprovedEvent
    | PlanRejectedEvent
    | ToolStartedEvent
    | ToolFinishedEvent
    | ToolFailedEvent
    | AgentDecisionEvent
    | BudgetExhaustedEvent
    | ClaimDraftedEvent
    | ClaimRejectedEvent
    | ClaimVerifiedEvent
    | VerdictEvent
    | ReviewDecidedEvent
    | PackageReadyEvent
    | ModelCallEvent
    | ErrorEvent
  )[];
  approved_plan_hash: string | null;
  /**
   * Regions the researcher drew in the viewer, kept as context.
   */
  regions: Region[];
}
/**
 * What the replay banner shows about the recording being played.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ReplayInfo".
 */
export interface ReplayInfo {
  recording_id: string;
  recorded_at: string;
  /**
   * live: recorded from real model calls; hand_authored: written for tests without calling a model.
   */
  origin: "live" | "hand_authored";
  question: string;
  note: string;
  /**
   * The dataset the recorded investigation ran on; the server's default when null.
   */
  dataset_id: string | null;
}
/**
 * state.json in the investigation's directory; events.jsonl beside it holds every event.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "InvestigationState".
 */
export interface InvestigationState {
  schema_version: string;
  investigation_id: string;
  question: string;
  run_mode: "immutable_replay" | "cached_tool_rerun" | "live";
  status: InvestigationStatus;
  dataset_id: string;
  replay: ReplayInfo | null;
  approved_plan_hash: string | null;
  created_at_utc: string;
  updated_at_utc: string;
  approved_at_utc: string | null;
  finished_at_utc: string | null;
  last_seq: number;
  /**
   * Regions the researcher drew in the viewer, kept as context.
   */
  regions: Region[];
}
/**
 * One participant's marker-positive cells, for drawing on the image: each cell's centroid and which of the audit
 * markers its whole-label mean reaches under the frozen thresholds. Positive for a marker, not a cell type: the masks
 * are nucleus-sized, so a label is the nucleus and a thin rim.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "KpmpCellMap".
 */
export interface KpmpCellMap {
  participant_id: string;
  /**
   * The measurement condition the positivity is read under.
   */
  condition: string;
  /**
   * Bit i of each cell's `positive` is markers[i].
   */
  markers: string[];
  thresholds: ProteinThreshold[];
  /**
   * All cells in the participant's table, positive or not.
   */
  total_cells: number;
  cell_id: number[];
  x_um: number[];
  y_um: number[];
  /**
   * Bitmask over `markers`; only cells positive for at least one are listed.
   */
  positive: number[];
  /**
   * Per listed cell, its whole-label mean of each marker (0-255), rounded to 0.1.
   */
  means: number[][];
  rule: string;
}
/**
 * A frozen positivity threshold on a marker's per-cell mean intensity.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ProteinThreshold".
 */
export interface ProteinThreshold {
  marker: string;
  value: number;
  rule: string;
  /**
   * The participant whose cells the threshold was derived from.
   */
  source_participant_id: string;
}
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "KpmpChannel".
 */
export interface KpmpChannel {
  channel_id: string;
  marker: string;
  label: string;
  description: string;
  /**
   * The raw intensity shown at full brightness.
   */
  display_max: number;
  tiles: KpmpTile[];
}
/**
 * One display image of a channel: a horizontal strip of the participant's image, placed by its bounds (µm).
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "KpmpTile".
 */
export interface KpmpTile {
  /**
   * Under the artifacts directory; served at /api/kpmp/files/<path>.
   */
  path: string;
  bounds: Region;
}
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "KpmpManifest".
 */
export interface KpmpManifest {
  dataset_id: string;
  participants: KpmpParticipant[];
  nucleus_threshold: ProteinThreshold;
  thresholds: ProteinThreshold[];
  results: KpmpResultEntry[];
  display_rule: string;
}
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "KpmpParticipant".
 */
export interface KpmpParticipant {
  participant_id: string;
  panel_id: string;
  role: string;
  title: string;
  extent: Region;
  pixel_size_um: number;
  cells: number;
  /**
   * Share of the image's pixels inside a segmentation label.
   */
  mask_coverage: number;
  median_cell_area_um2: number;
  mask_note: string;
  channels: KpmpChannel[];
  /**
   * Clinical values from downloaded KPMP files only; empty when none is downloaded.
   */
  clinical: {
    [k: string]: string;
  };
  clinical_note: string;
  source_files: string[];
}
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "KpmpResultEntry".
 */
export interface KpmpResultEntry {
  participant_id: string;
  population_marker: string;
  marker: string;
  label: EvidenceStatus;
  path: string;
}
/**
 * One section's cells counted by cell type label under each rule, and the cells whose label differs.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "LabelCounts".
 */
export interface LabelCounts {
  cells: number;
  /**
   * Per label rule id, cells per cell type label.
   */
  cell_types: {
    [k: string]: {
      [k: string]: number;
    };
  };
  differing_cells: number;
  /**
   * Cells per 'first-rule label -> second-rule label' change.
   */
  differing: {
    [k: string]: number;
  };
}
/**
 * A frozen, named rule that assigns cell type labels from marker counts under the default condition.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "LabelRule".
 */
export interface LabelRule {
  label_rule_id: string;
  description: string;
  /**
   * Marker genes per cell type, in tie-break order.
   */
  markers: {
    [k: string]: string[];
  };
  /**
   * Genes the rule never reads when it decides membership.
   */
  ignored_genes: string[];
  /**
   * A cell's top marker score (count / gene scale) must reach this.
   */
  score_threshold: number;
  /**
   * A cell with fewer default molecules is labelled 'Low quality'.
   */
  min_molecules: number;
}
/**
 * The measure under one label rule.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "LabelRuleArm".
 */
export interface LabelRuleArm {
  label_rule_id: string;
  finding_id: string;
  /**
   * Cells of the population summed over every counted section.
   */
  cells_labelled: number;
  cells_labelled_by_section: {
    [k: string]: number;
  };
  eligible_section_ids: string[];
  pooled: PooledConditionValue[];
  label: EvidenceStatus;
  label_reason: string;
}
/**
 * The frozen label rules of a dataset, the gene scales they use, and per-section label counts.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "LabelRuleSet".
 */
export interface LabelRuleSet {
  schema_version: string;
  dataset_id: string;
  rules: LabelRule[];
  default_label_rule_id: string;
  /**
   * Mean default molecules of each gene per expressing cell, pooled over the scale sections.
   */
  gene_scales: {
    [k: string]: number;
  };
  gene_scale_sections: string[];
  sections: {
    [k: string]: LabelCounts;
  };
  notes: string[];
  citation: string;
}
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "LabelSensitivityCheck".
 */
export interface LabelSensitivityCheck {
  schema_version: string;
  control_kind: "label_sensitivity";
  control_id: string;
  dataset_id: string;
  cell_type: string;
  genes: string[];
  measure: string;
  /**
   * @minItems 2
   * @maxItems 2
   */
  arms: [LabelRuleArm, LabelRuleArm];
  /**
   * Cells labelled with the population under both rules.
   */
  cells_in_both: number;
  cells_only_first: number;
  cells_only_second: number;
  /**
   * Both rules give the same evidence label.
   */
  same_label: boolean;
  summary: string;
  roi: Region | null;
}
/**
 * How the server answers questions. Live runs arrive with ticket 03.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ModeInfo".
 */
export interface ModeInfo {
  dataset_id: string;
  default_run_mode: "immutable_replay" | "cached_tool_rerun" | "live";
  available_run_modes: ("immutable_replay" | "cached_tool_rerun" | "live")[];
  recordings: ReplayInfo[];
}
/**
 * Everything sent to a provider. Its content hash keys the cache and the replay (ADR-0003),
 * so it must never contain ids, timestamps or other run-specific values.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ModelRequest".
 */
export interface ModelRequest {
  provider: "meta" | "baseten" | "fireworks";
  model: string;
  messages: ChatMessage[];
  response_schema: {
    [k: string]: unknown;
  } | null;
  /**
   * Every model here reasons before answering; a small cap returns empty content.
   */
  max_tokens: number;
  reasoning_effort: "low" | "medium" | "high";
  api: "chat_completions" | "responses" | "sam_segmentation" | "asr_transcribe";
  /**
   * Muse Voice Transcribe: terms to bias recognition toward, such as panel gene names. Left out of the cache key when empty, so requests stored before this field existed keep their keys.
   */
  keywords: string[];
}
/**
 * What a provider returned. `finish_reason` is "length" when the token cap cut the answer short, on either
 * endpoint. `served_by` names the provider that answered when it differs from the requested one (failover).
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ModelResponse".
 */
export interface ModelResponse {
  content: string;
  finish_reason: string;
  usage: TokenUsage | null;
  served_by: ("meta" | "baseten" | "fireworks") | null;
  /**
   * SAM 3.1: the streamed response events, kept so a stored response is parsed exactly as a live one.
   */
  events:
    | {
        [k: string]: unknown;
      }[]
    | null;
  audio_duration_ms: number | null;
}
/**
 * One entry per molecule, column by column, so a whole section ships compactly.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "MoleculeColumns".
 */
export interface MoleculeColumns {
  x: number[];
  y: number[];
  /**
   * Index into RegionView.genes.
   */
  gene_index: number[];
  /**
   * Index into the cell columns; -1 for an unassigned molecule.
   */
  cell_index: number[];
  /**
   * Per condition, 1 if the molecule counts toward its cell under that condition, else 0.
   */
  included: {
    [k: string]: number[];
  };
}
/**
 * One candidate outline of a seed (the seed box, the convex hull of its NPHS1 clusters, or the SAM 3.1
 * outline) measured the same way, so what SAM adds over the cruder shapes is visible.
 *
 * - `seed_box_coverage`: the share of the seed box's area the shape covers.
 * - `retention`: the structure-constrained condition with this shape as the only structure, over default
 *   molecules whose molecule or cell centroid lies inside it: the share kept.
 * - PECAM1 (endothelium) and PDGFRB (mesangium) consistency: each gene's molecule density inside the shape over
 *   its density in the rest of the seed's crop, and the share of the crop's molecules of the gene inside.
 *   Glomerular tufts carry both; neither gene seeded the box.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "OutlineMeasures".
 */
export interface OutlineMeasures {
  shape: "seed_box" | "convex_hull" | "sam_outline";
  area_um2: number | null;
  seed_box_coverage: number | null;
  default_molecules: number;
  kept_molecules: number;
  retention: number | null;
  pecam1_enrichment: number | null;
  pdgfrb_enrichment: number | null;
  pecam1_share_inside: number | null;
  pdgfrb_share_inside: number | null;
  missing_reasons: {
    [k: string]: string;
  };
}
/**
 * manifest.json inside the evidence package: what it contains and how it was produced.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "PackageManifest".
 */
export interface PackageManifest {
  schema_version: string;
  package_id: string;
  investigation_id: string;
  created_at: string;
  run_mode: "immutable_replay" | "cached_tool_rerun" | "live";
  replay: ReplayInfo | null;
  question: string;
  dataset: DatasetManifest;
  plan_id: string | null;
  plan_hash: string | null;
  files: FileChecksum[];
  audit_log: ChainCheckResult;
  review_state: "work_in_progress" | "reviewed";
  claims: number;
  notes: string[];
  /**
   * What the investigation could not settle within its budget.
   */
  open_questions: OpenQuestion[];
  /**
   * Review decisions recorded so far (reviews.json).
   */
  reviews: number;
}
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "PackedCellColumns".
 */
export interface PackedCellColumns {
  count: number;
  cell_id: string[];
  x: PackedColumn;
  y: PackedColumn;
  nucleus_radius: PackedColumn;
  cell_type_index: PackedColumn;
}
/**
 * One column as a base64 string of little-endian values, decoded straight into a typed array.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "PackedColumn".
 */
export interface PackedColumn {
  dtype: "float32" | "uint8" | "int32";
  data: string;
}
/**
 * Every molecule of the view, one typed column each.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "PackedMoleculeColumns".
 */
export interface PackedMoleculeColumns {
  count: number;
  x: PackedColumn;
  y: PackedColumn;
  gene_index: PackedColumn;
  cell_index: PackedColumn;
  inclusion_bits: PackedColumn;
  condition_bits: {
    [k: string]: number;
  };
}
/**
 * A region view in typed columns, compact enough to ship and draw a whole section of several hundred
 * thousand molecules at once.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "PackedRegionView".
 */
export interface PackedRegionView {
  schema_version: string;
  encoding: "base64-little-endian-v1";
  dataset_id: string;
  section_id: string;
  section_name: string | null;
  group: string | null;
  synthetic: boolean;
  region: Region;
  label_rule_id: string;
  genes: string[];
  cell_types: string[];
  molecules: PackedMoleculeColumns;
  cells: PackedCellColumns;
  structures: StructureMask[];
  notes: string[];
}
/**
 * The outline of one structure in section coordinates (micrometres), as a closed polygon.
 *
 * `source` says where the outline came from: drawn by construction in a synthetic fixture, or proposed
 * by SAM 3.1 from a box prompt (ADR-0005), which the UI must label as a proposal.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "StructureMask".
 */
export interface StructureMask {
  schema_version: string;
  structure_id: string;
  section_id: string;
  kind: "glomerulus";
  outline: number[][];
  source: "synthetic" | "sam-3.1";
  /**
   * SAM 3.1 outlines: the version of the finder's frozen rules.
   */
  mask_version: string | null;
  /**
   * SAM 3.1 outlines: the structure-finder run that proposed it.
   */
  run_id: string | null;
  /**
   * SAM 3.1 outlines: the seed box it was prompted with.
   */
  seed_id: string | null;
}
/**
 * The planner model's structured output, before it is checked against the tool registry.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "PlanProposal".
 */
export interface PlanProposal {
  summary: string;
  contrast: Contrast | null;
  cell_types: string[];
  conditions: ConditionName[];
  steps: ProposedStep[];
  /**
   * The question split into testable sub-claims, each with the hypothesis's prediction.
   */
  sub_claims: SubClaim[];
}
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ProposedStep".
 */
export interface ProposedStep {
  tool: string;
  arguments: {
    [k: string]: unknown;
  };
  rationale: string;
}
/**
 * How the share of one marker's positive cells in a population behaves across measurement conditions, for one
 * participant, over the whole image or a region. One participant against another is descriptive only.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ProteinAuditResult".
 */
export interface ProteinAuditResult {
  result_id: string;
  dataset_id: string;
  participant_id: string;
  /**
   * 'healthy reference' or 'diseased'.
   */
  role: string;
  roi: Region | null;
  /**
   * The population, frozen under the whole-cell condition, for example 'Podocalyxin+ cells'.
   */
  population: string;
  population_marker: string;
  marker: string;
  /**
   * The marker's home cells, for example 'LRP2+ cells that are not Podocalyxin+'.
   */
  home: string;
  population_cells: number;
  home_cells: number;
  thresholds: ProteinThreshold[];
  conditions: ProteinConditionRow[];
  label: EvidenceStatus;
  label_reason: string;
  inference: string;
  rules: {
    [k: string]: string;
  };
  /**
   * sha256 of the per-cell table the result was computed from.
   */
  cell_table_checksum: string;
}
/**
 * The result under one measurement condition. Population cells with no pixel kept count as not positive.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ProteinConditionRow".
 */
export interface ProteinConditionRow {
  condition: string;
  /**
   * Population cells whose mean of the marker under this condition is at or above its threshold.
   */
  positive_cells: number;
  observed_share: number | null;
  /**
   * Random-pixel-loss expectation: the mean over population cells of the probability that a random subset of the cell's pixels, as large as this condition keeps, has a mean at or above the threshold.
   */
  expected_share: number | null;
  /**
   * Population pixels kept under this condition / population pixels of the whole cells.
   */
  pixel_retention: number | null;
  /**
   * Population cells positive for the marker as whole cells but not under this condition.
   */
  excluded_cells: number;
  /**
   * Population cells positive for the marker as whole cells and under this condition.
   */
  retained_cells: number;
  /**
   * Share of the excluded cells that border a home cell.
   */
  bordering_home_share_excluded: number | null;
  /**
   * Share of the retained cells that border a home cell.
   */
  bordering_home_share_retained: number | null;
  /**
   * Why a value is null.
   */
  reasons: {
    [k: string]: string;
  };
}
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "RandomThinningControl".
 */
export interface RandomThinningControl {
  schema_version: string;
  control_kind: "random_thinning";
  control_id: string;
  finding_id: string;
  dataset_id: string;
  label_rule_id: string;
  cell_type: string;
  genes: string[];
  measure: string;
  eligible_section_ids: string[];
  pooled: PooledConditionValue[];
  /**
   * Every section's values; only eligible ones are pooled.
   */
  sections: AuditSectionValues[];
  /**
   * The frozen audit threshold the verdict uses.
   */
  threshold: string;
  conditions_below_threshold: ConditionName[];
  label: EvidenceStatus;
  label_reason: string;
  roi: Region | null;
}
/**
 * Boxes on a section whose SAM 3.1 box-prompt response is stored, so a cached tool rerun can outline them
 * without a model call. Any other box needs a live run.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "RecordedBoxes".
 */
export interface RecordedBoxes {
  section_id: string;
  boxes: Region[];
}
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "RecordedCall".
 */
export interface RecordedCall {
  purpose: string;
  cache_key: string;
  request: ModelRequest;
  inputs: CacheInput[];
  response: ModelResponse;
  latency_ms: number | null;
}
/**
 * A recorded investigation's model responses, replayed by content hash of each request.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "Recording".
 */
export interface Recording {
  schema_version: string;
  info: ReplayInfo;
  calls: RecordedCall[];
}
/**
 * Everything the viewer draws for one region of a section, in micrometres.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "RegionView".
 */
export interface RegionView {
  schema_version: string;
  dataset_id: string;
  section_id: string;
  synthetic: boolean;
  region: Region;
  label_rule_id: string;
  genes: string[];
  cell_types: string[];
  molecules: MoleculeColumns;
  cells: CellColumns;
  structures: StructureMask[];
  notes: string[];
}
/**
 * A review decision as the client sends it; the server adds the claim version, the time and the id.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ReviewRequest".
 */
export interface ReviewRequest {
  decision: "accepted_for_follow_up" | "needs_investigation" | "unresolved";
  reviewer: string;
  via: "click" | "voice";
  confirmed: boolean;
}
/**
 * The output artifact of the `audit_section` tool.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "SectionAudit".
 */
export interface SectionAudit {
  schema_version: string;
  artifact_id: string;
  dataset_id: string;
  section_id: string;
  conditions: ConditionName[];
  metrics: AuditMetrics[];
  excluded_molecule_ids: {
    [k: string]: string[];
  };
}
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "StartInvestigationRequest".
 */
export interface StartInvestigationRequest {
  question: string;
  run_mode: "immutable_replay" | "cached_tool_rerun" | "live";
  /**
   * The dataset to investigate; the server's default when omitted. A recording names its own.
   */
  dataset_id: string | null;
  /**
   * Regions the researcher drew in the dual-section viewer (one per section), kept with the investigation as context and shown beside its verdicts. Each must lie on a section of the investigated dataset. They do not scope the analysis or reach any model prompt. Ignored by immutable replay, which returns a recorded investigation.
   *
   * @maxItems 2
   */
  regions: [] | [Region] | [Region, Region];
}
/**
 * What SAM 3.1 proposed for one seed. Empty, fragmented and rejected proposals are kept, never forced:
 * - outlined: one connected piece that passes the geometric checks;
 * - fragmented: several pieces; the largest is outlined and the count recorded;
 * - empty: no mask came back, or it has no pixels;
 * - rejected: a geometric check failed (see the run's `rejection_rule`), or the seed was never sent.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "StructureProposal".
 */
export interface StructureProposal {
  seed: StructureSeed;
  status: "outlined" | "fragmented" | "empty" | "rejected";
  reason: string | null;
  /**
   * The structure mask built from it; null when it is empty or rejected.
   */
  structure_id: string | null;
  fragments: number;
  /**
   * The image it was sent in, by index into the run's crops.
   */
  crop_index: number | null;
  comparisons: OutlineMeasures[];
}
/**
 * One box prompt: merged NPHS1 clusters (one per glomerulus, padded), or a box the researcher drew.
 * NPHS1 seeds the box, so it is never used to judge the outline.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "StructureSeed".
 */
export interface StructureSeed {
  seed_id: string;
  section_id: string;
  origin: "nphs1_clusters" | "user_box";
  box: Region;
  /**
   * NPHS1 molecules in the merged clusters; null for a user box.
   */
  nphs1_molecules: number | null;
  /**
   * NPHS1 clusters merged into this seed; null for a user box.
   */
  clusters_merged: number | null;
}
/**
 * One run of the structure finder on one section: the images sent to SAM 3.1, what came back for every seed,
 * and the outlines kept. Exploratory (ADR-0006): the outlines feed only the structure-constrained condition,
 * which never enters an evidence label.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "StructureRun".
 */
export interface StructureRun {
  schema_version: string;
  run_id: string;
  mask_version: string;
  dataset_id: string;
  section_id: string;
  model: string;
  run_mode: "cached_tool_rerun" | "live";
  badge: "SAM 3.1 proposal (exploratory)";
  seeding_rule: string;
  rendering_rule: string;
  rejection_rule: string;
  images_sent: number;
  /**
   * Live spend for a live run; for a stored run, what the same images cost at list price.
   */
  estimated_cost_usd: number;
  crops: Region[];
  proposals: StructureProposal[];
  structures: StructureMask[];
}
/**
 * A tool as the planner sees it in the registry.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ToolSpec".
 */
export interface ToolSpec {
  name: string;
  version: string;
  description: string;
  arguments_schema: {
    [k: string]: unknown;
  };
}
/**
 * What Muse Voice Transcribe heard. Nothing runs on it until the researcher confirms the edited text.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "Transcription".
 */
export interface Transcription {
  transcript: string;
  /**
   * `cached_tool_rerun` serves a stored response; `live` made a fresh call.
   */
  run_mode: "immutable_replay" | "cached_tool_rerun" | "live";
  source: "live" | "replay" | "cache";
  model: string;
  /**
   * The panel genes recognition was biased toward.
   */
  keywords: string[];
  /**
   * The clip's length, read from its WAV header.
   */
  audio_duration_ms: number;
  latency_ms: number;
}
