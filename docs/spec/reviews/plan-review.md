> **Status (Nov 2 2026):** Answered in spec and tickets revision 2; see `docs/spec/review-response.md`.

# SpatialScout spec and ticket review

Reviewed November 2, 2026 against repository commit `d747609`, the working tree, build whitepaper v2, the five ADRs, research notes and spike source code. This is a design and readiness review, not a rerun of the scientific experiments or a deployment test. The untracked marker-pair script was treated as unfinished work, not an implemented capability. No repository files or issues were changed.

## Verdict

Keep the project and broad platform vision. The new spec is more feasible than the original PRD because it reflects actual data availability, uses computed results and distinguishes research evidence from verification. However, the current plan needs scientific and dependency corrections before the tickets are treated as fully ready for implementation.

The 14 tickets exist in `docs/spec/tickets-draft.md` and are explicitly marked unpublished. A read-only GitHub query for all issues in `chandrarup/spatialscout` returned none at review time. Ticket numbers below refer to the local draft, not GitHub issue numbers.

## What remains strong

- Comparing assignment conditions from deposited molecule flags is a defensible, feasible first capability when images and boundaries are absent. It measures sensitivity; it does not establish correction accuracy.
- The split viewer, retention display and claim-to-region navigation make the evidence inspectable.
- Separate evidence, verification and review statuses preserve important distinctions.
- A real agent investigation with bounded tools, measured verification and an exportable evidence package remains a coherent product.
- Labelled replay protects access during judging. A bounded live path should remain demonstrable.
- Deferring fine-tuning, urine integration and additional datasets is appropriate for this release, while preserving them in the platform roadmap.

## Required changes

### 1 Restore donor independence as an inference gate

Priority: high. Affects tickets 02 and 06; spec lines 107 and 147–153; ADR-0002.

The spec makes sections the replication unit even though the data-readiness note records repeated donors. Disclosing that limitation and leaving out one section do not make correlated sections independent. Integer molecule counts satisfy an input constraint; they do not establish that a PyDESeq2 analysis is statistically valid.

Require verified section-to-donor mapping for donor-level inference. If available, aggregate appropriately and assess influence by leaving out donors. If unavailable, keep the DKD section-level contrast descriptive, suppress inferential p-values and confidence claims that assume independent sections, and explicitly record the inferential limitation. Do not infer donor identity from gene-expression similarity and treat it as confirmed metadata.

The reported IgAN group has four sections and four donors, making it a candidate for further verification if a replicated contrast is needed. It is not automatically validated by this review. The DKD visual investigation can remain the demonstration regardless.

### 2 Give the hero question its own evidence type

Priority: high. Affects tickets 06, 09 and 10; spec Claim/Finding contracts.

The spike's evidence that LRP2/CUBN co-expression remains under nucleus-only assignment is not the same quantity as a DKD-versus-Control log2 effect. Currently a Finding is defined only as a disease contrast, while the hero narrative asks whether a reported cell state survives assignment restrictions. Those are different scientific questions.

Add a descriptive assignment-audit result with per-section co-expression, molecule retention and nuclear-overlap summaries. Claims may reference that result without pretending it is differential expression. A disease-contrast result should be a separate typed result with its own inference eligibility.

Use wording such as: “Co-expression persists under the tested restriction in cells labelled by our marker rule.” Do not imply replication of the authors' cell labels or proof of a biological state. Since LRP2/CUBN help distinguish proximal-tubule cells in the spike's label rule, add a documented ambiguity/label-sensitivity check for the hero population. Freezing labels removes between-condition relabelling, but does not remove selection bias in the original label assignment.

### 3 Make the first complete release independent of SAM and voice

Priority: high. Affects ticket 12 dependencies and the 06 → 09 → 10 → 11 chain.

Ticket 12 is blocked by 07 and 08, making SAM and voice mandatory for the final package. Ticket 09 depends on all of 06, so a delay in disease inference also blocks agent integration, verification and export. This contradicts the whitepaper's module-by-module fallback strategy.

Split ticket 09 into an initial audit investigation and later disease-contrast support. Allow early verification and export of descriptive audit results. Remove 07 and 08 as hard blockers for the first recorded release. Keep them as improvements that can be integrated when ready. Ticket 11 should permit click-based review without voice.

Replace the requirement to show at least one sensitive finding with an evidence-driven requirement: open representative valid evidence, and show sensitive findings only if the final pipeline produces them. Reserve final labels until the analysis configuration is frozen.

### 4 Keep inferred SAM boundaries out of the primary evidence labels

Priority: high if used to establish scientific conclusions. Affects ticket 07, ADR-0005 and the frozen condition list.

The box-prompt spike supports a promising interaction on rendered nucleus geometry. It does not independently validate anatomical boundaries. Other marker enrichment is a consistency check, and higher enrichment can result from a smaller mask that omits legitimate tissue. A synthetic mask-placement test validates coordinates, not kidney anatomy.

Initially use SAM proposals for navigation and an explicitly exploratory condition. Compare them with the seed boxes and a simple geometric baseline; report coverage and retention alongside enrichment. Permit empty, fragmented or rejected proposals rather than requiring an outline for every seed. An independently checked subset is needed for an anatomical accuracy claim.

Do not let this later optional condition silently change primary labels. Store the condition set, mask version and run identity, and present primary versus exploratory outputs separately. This recommendation narrows the scientific use specified in ADR-0005 and should be recorded as an explicit decision change.

### 5 Tighten acceptance tests for analytical sensitivity

Priority: high before publishing results. Affects tickets 05 and 06.

The spike scan applies the molecule count gate to the default condition only, and checks leave-one-section-out direction for that condition only. Its reversal rule also has a 0.2 magnitude threshold and compares only default with nucleus-only, unlike the prose spec. These are exploratory results, so recompute rather than importing their labels into the final application.

Specify gate precedence, condition eligibility, minimum valid-condition count, near-zero effect handling, and influence checks across all required conditions. An inadequately measured condition must not create an apparent sensitive effect. Distinguish fixed cell populations from cells retaining measurable molecules. Freeze normalization and report the multiple-testing family wherever inferential tests are supported.

Add a retention-matched random-thinning control. A co-expression proxy can decrease merely because fewer molecules remain; retention displayed alongside it does not by itself separate that effect from spatially informative exclusion. This is a proposed evaluation improvement, not evidence that any current result is wrong.

### 6 Define persisted investigation state and honest replay semantics

Priority: medium to high. Affects tickets 01, 03, 04 and 09; ADRs 0003–0004.

The spec combines long SSE streams, human approval and a 150-second live target without defining persistent state, resumption or concurrent approvals. Modal documents a 150-second HTTP request limit and a job-ID/polling pattern; do not assume SSE exempts the workflow from that constraint.

Persist investigation status and ordered events independently of an individual connection. Start jobs with an ID, make approval idempotent, and allow reconnection or polling from the last delivered event. Test a refresh at approval, reconnection during execution and duplicate approval. Store live spend reservations durably and atomically if parallel drafting is enabled.

Distinguish three modes: immutable event playback; tool re-execution with cached model responses; and a fresh live investigation. Replay should not resume current timestamps while presenting old operations as newly executed. Include data, tool and artifact versions in cache identity, not only prompt text.

## Revised delivery order

| Stage | Tickets | Exit condition |
|---|---|---|
| Foundation | 01, then 02 / 03 / 04 | Real data visible; gateway usable; public skeleton works |
| First real investigation | 05 + initial 09 + basic 10 and 11 | Ask, audit, inspect, check, review and export |
| Evidence quality | Corrected 06 and extended 10 | Properly labelled contrast or descriptive results; benchmark recorded |
| First submission candidate | 12 | Real run recorded, replay tested and claims traced |
| Enhancements | 07 and 08 | Optional features improve the working demonstration |
| User value | 13 preparation early; session after usable investigation | Observed feedback informs one concrete improvement |
| Stretch | 14 only after 12 | Offline agreement study, not a new accuracy claim |

Make ticket 14 depend explicitly on 12 if the issue graph is published. Training on the marker rule and measuring agreement with that rule demonstrates imitation, not independently validated cell-type accuracy. Donor overlap also matters when selecting evaluation partitions.

## Judging implications and correction to the earlier assessment

The official waiver contains weights: Impact 30%, Use of Meta AI Tooling 25%, Technical Depth and Execution 20%, Demo 25%. I verified the embedded content in the official waiver HTML during this review. My earlier inability to confirm those weights should no longer guide the plan.

The strongest investment is a credible researcher decision with a dependable demonstration. Show that the agent chooses useful next checks, exposes uncertainty, catches defined errors and saves demonstrable work. The rubric rewards substantive use of Meta tooling, not a specified count of models or inference partners.

Retain the wider platform story, but describe this release as an assignment-sensitivity investigation workspace. Evidence of faster or more reliable investigation would strengthen Impact. A user-feedback session can start before the complete export and full benchmark are finished; recording observed results remains conditional on actual participation.

## Other cleanup before implementation

- Mark the old root PRD as superseded for execution. It contains scripted gains and incompatible requirements. The current spec already states which sources win, but agents can still find the old document first.
- Reconcile the research notes' differing statements on judging weights and provider structured-output guarantees. A successful smoke response shows compatibility for that request, not guaranteed schema enforcement; keep local validation and bounded repair.
- Finish and freeze the reference-derived marker-pair artifact before evaluation. The untracked script is still a placeholder at review time. Do not claim the reference evaluation has already happened.
- State exactly what numerical verification recomputes. Independently checking sums and claim direction is different from independently reproducing a fitted model and confidence interval.
- A hash chain detects edits relative to a trusted chain value; it does not prevent someone from rewriting the whole chain. Qualify the integrity claim or anchor the exported digest outside the mutable log.

## External sources checked

- [Official event waiver and judging rubric](https://cerebralvalley.ai/e/meta-ai-developer-hackathon/waiver)
- [Modal request timeouts and asynchronous polling pattern](https://modal.com/docs/guide/webhook-timeouts)
- [Modal streaming endpoints](https://modal.com/docs/guide/streaming-endpoints)

Local review anchors: `docs/spec/spec.md` lines 107–115 and 147–153; `docs/spec/tickets-draft.md` ticket sections 02, 05–12 and 14; `docs/research/data-readiness.md`; `docs/research/spikes.md`; `spikes/science_spike.py`; `spikes/science_scan.py`; ADRs 0001–0005; and `docs/product/build-whitepaper-v2.md`.
