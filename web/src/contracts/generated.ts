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
  | ToolStartedEvent
  | ToolFinishedEvent
  | ClaimDraftedEvent
  | PackageReadyEvent
  | ModelCallEvent
  | ErrorEvent;
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "InvestigationStatus".
 */
export type InvestigationStatus = "planning" | "awaiting_approval" | "running" | "complete" | "failed";
/**
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "RunMode".
 */
export type RunMode = "immutable_replay" | "cached_tool_rerun" | "live";

export interface SpatialScoutContracts {}
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
    | "tool_call"
    | "claim_drafted"
    | "package_exported"
    | "error";
  payload: {
    [k: string]: unknown;
  };
  prev_hash: string;
  entry_hash: string;
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
   * One gene, or a gene pair for co-expression.
   *
   * @minItems 1
   * @maxItems 2
   */
  genes: [string] | [string, string];
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
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "AuditSectionValues".
 */
export interface AuditSectionValues {
  section_id: string;
  cells_labelled: number;
  conditions: AuditConditionValue[];
}
/**
 * A region ranked by the result's ranking rule as showing the molecules behind it (rank 1 is first).
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "EvidenceRegion".
 */
export interface EvidenceRegion {
  rank: number;
  region: Region;
  score: number | null;
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
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "Budget".
 */
export interface Budget {
  max_tool_calls: number;
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
 * The difference between group means of the log2 values under one condition.
 *
 * This interface was referenced by `SpatialScoutContracts`'s JSON-Schema
 * via the `definition` "ConditionEffect".
 */
export interface ConditionEffect {
  condition: ConditionName;
  effect: number | null;
  missing_reason: string | null;
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
    | ToolStartedEvent
    | ToolFinishedEvent
    | ClaimDraftedEvent
    | PackageReadyEvent
    | ModelCallEvent
    | ErrorEvent
  )[];
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
}
