> **Status (Nov 2 2026):** Adopted with corrections in spec and tickets revision 2; see `docs/spec/review-response.md`. Where this directive and the spec differ, the spec wins.

# Agent Directive: Turning the Reviewer Audit Into a 1st-Place Hackathon Build (Without Violating ADR-0001)

> **Instructions for the Coding Agent:** Read this document carefully alongside `CLAUDE.md`, `GLOSSARY.md`, `docs/adr/0001`–`0005`, `docs/spec/spec.md`, `docs/spec/tickets-draft.md`, and the Reviewer Audit notes (Points 2–6). Evaluate how the patterns below satisfy **100% of the reviewer's scientific and architectural critiques** while preventing a critical failure mode: building a scientifically cautious but visually passive table viewer where the AI agent appears superfluous. Adopt these refinements into `docs/spec/spec.md`, `docs/spec/tickets-draft.md`, and your implementation immediately.

## 1. The Core Strategic Problem: Why Cautious Compliance Alone Will Lose the Hackathon

The [Meta Global AI Developer Hackathon](https://cerebralvalley.ai/e/meta-ai-developer-hackathon) is scored on four official weights verified in the [event waiver](https://cerebralvalley.ai/e/meta-ai-developer-hackathon/waiver):
* **Impact (30%)**
* **Use of Meta AI Tooling (25%)**
* **Demo (25%)**
* **Technical Depth & Execution (20%)**

Right now, our repo has exceptional discipline (`ADR-0001`: every number comes from a computed artifact; `ADR-0002`: integer molecule subsets; `ADR-0003`: replay by default; `ADR-0005`: `SAM 3.1` box prompts on RNA-derived images). **However, look at what happens if we implement the reviewer's notes purely defensively:**
1. If all confounder checks (random-thinning control, label-rule circularity, count gates, leave-one-section-out) are computed silently inside a monolithic Python batch script before the agent ever speaks, **the agent does no scientific reasoning**—it merely reads rows of a pre-computed table and writes one summary sentence per row. A finalist judge watching that demo will ask: *"Why did you need an AI agent here? Couldn't this just be a static Scanpy dashboard?"*
2. If we demote `SAM 3.1` (Ticket 07) to an optional background overlay that is hidden from the main findings view (an over-literal reading of Reviewer Point #4), we gut our strongest visual showcase for the **25% Use of Meta AI Tooling** and **25% Demo** scores.
3. If we implement Reviewer Point #5 (retention-matched random-thinning control) via Monte Carlo permutation loops across 22 [GSE286184](https://pmc.ncbi.nlm.nih.gov/articles/PMC13586693/) sections and Reviewer Point #6 ([Modal 150s timeout](https://modal.com/docs/guide/webhook-timeouts)) via heavy database plumbing, we will miss the **Wednesday, November 4 (1:00 PM CT) code freeze**.

**The Solution:** We keep 100% of `ADR-0001` (zero faked numbers, zero overclaimed biology), adopt all five of the reviewer's structural fixes using **closed-form math and lightweight file persistence**, and turn the reviewer's methodological checks into **observable, high-impact agentic reasoning steps** on screen.

## 2. Fast-Path Implementation of Reviewer Points 2–6 (Zero Scope Creep)

### 2.1 Reviewer Point #2: Split `Finding` Into `DescriptiveAuditResult` and `DiseaseContrastFinding` + 1-Line Circularity Fix

* **Why the Reviewer is Right:** In [GSE286184](https://pmc.ncbi.nlm.nih.gov/articles/PMC13586693/), our hero biological question (*"Do podocytes co-expressing `LRP2`/`CUBN` ['Podocyte endocytosis'] retain that co-expression under `nucleus_only` assignment, while `UMOD` in B-cells collapses?"*) is a **within-cell-type assignment-sensitivity question** (Ticket 05), not a `DKD vs Control` `PyDESeq2` differential expression contrast (Ticket 06, where rare podocytes often hit count gates).
* **How to Implement Cleanly (Tickets 01, 05, 06, 09, 10):**
  1. Make `Finding` a discriminated union (`finding_kind: "descriptive_audit" | "disease_contrast"`) so `Claim` (Ticket 09) and `Verifier` (Ticket 10) can cite either a descriptive assignment-audit result (per-section co-expression, molecule retention, nuclear overlap, and thinning control) **or** a disease-contrast result (`DKD vs Control` `PyDESeq2` log2 fold change).
  2. **Fix `LRP2`/`CUBN` Label Circularity in 10 Lines (Not a Separate Pipeline):** In Ticket 02's frozen marker rule, define `Podocyte` strictly by canonical podocyte markers (`NPHS1`, `NPHS2`, `PODXL`, `WT1`) and record a single deterministic diagnostic field on `DescriptiveAuditResult`: `label_sensitivity_check` (reporting the exact count and % of podocyte-labelled cells and `LRP2`/`CUBN` co-expression when `LRP2`/`CUBN` are excluded from vs. included in the proximal-tubule exclusion gate).

### 2.2 Reviewer Point #3: Unblock the Critical Path (`09a` / `09b` Split)

* **Why the Reviewer is Right:** Blocking Ticket 09 (Agent loop) on all of Ticket 06 (`PyDESeq2` contrasts) and blocking Ticket 12 (Golden path) on Tickets 07 (`SAM 3.1`) and 08 (`Voice`) creates a single-point failure chain.
* **How to Implement Cleanly (Tickets 06–12):**
  * **Ticket 09a (Immediate after 03 + 05):** Wire the full agent loop (`Muse Wonder` plan → approval → `Muse Spark 1.3` tool calls → `Baseten Muse Spark Open` parallel claim drafting) against Ticket 05's `DescriptiveAuditResult` first. This immediately unlocks Ticket 10 (Verifier) and Ticket 11 (Review & Export) on real [GSE286184](https://pmc.ncbi.nlm.nih.gov/articles/PMC13586693/) data (`LRP2`/`CUBN` in podocytes and `UMOD` in B-cells).
  * **Ticket 09b (Merge when 06 finishes):** Register the `compute_disease_contrast` tool into the existing agent loop once Ticket 06 passes its seam-1 tests.
  * **Tickets 07 (`SAM 3.1`) and 08 (`Voice`):** Treat as progressive enhancements that plug into the working application rather than hard gates blocking initial verification and export testing.

### 2.3 Reviewer Point #4: Keep `SAM 3.1` Visually Central While Protecting Primary Evidence Labels

* **Why We Must Balance Rigor With Hackathon Judging:** The reviewer rightly notes that `SAM 3.1` box-prompt outlines on nucleus-rendered images are unvalidated against expert pathology annotation and should not silently flip primary evidence labels. However, **Use of Meta AI Tooling is 25% of the hackathon score**.
* **How to Implement Cleanly (Tickets 05, 06, 07):**
  * Compute the frozen `evidence_label` (`stable`, `segmentation_sensitive`, `insufficient_evidence`) strictly over the primary geometric conditions (`default`, `nucleus_only`, `distance_1um`, `distance_2um`).
  * Keep `structure_constrained` (`SAM 3.1` glomerulus masks) in the main UI table, the split-screen slider, and the finding figures as a dedicated column/layer explicitly badged **`SAM 3.1 Proposal (Exploratory)`**, displaying seed-box coverage, molecule retention, and `PECAM1`/`PDGFRB` tuft consistency right beside it.

### 2.4 Reviewer Point #5: Closed-Form Retention-Matched Random-Thinning Control (2ms in NumPy, Zero Monte Carlo Loops)

* **Why the Reviewer is Right:** When `nucleus_only` drops 50–60% of molecules in a cell, co-expression of any marker pair $(g, h)$ will naturally decrease simply because fewer molecules remain. Displaying `retention` beside the number does not tell the user how much of the drop is expected from random molecule loss versus removing spatially admixed neighbor transcripts.
* **How to Implement in 10 Lines of Vectorized NumPy (No Simulation Delay):**
  For each cell $c$ with default counts $k_{c,g}, k_{c,h}$ and observed condition retention ratio $r_c = N_{c,\text{cond}} / N_{c,\text{default}} \in [0, 1]$, under uniform independent random thinning at rate $r_c$, the exact probability that gene $g$ retains $\ge 1$ molecule in cell $c$ is:
  $$p_{c,g} = 1 - (1 - r_c)^{k_{c,g}}, \qquad p_{c,h} = 1 - (1 - r_c)^{k_{c,h}}$$
  Summing over all cells in the section/population gives the exact analytical random-thinning expectation:
  $$E_{\text{thin}}[\text{both}] = \sum_c p_{c,g} p_{c,h}, \qquad E_{\text{thin}}[\text{either}] = \sum_c \left(p_{c,g} + p_{c,h} - p_{c,g} p_{c,h}\right), \qquad C_{\text{thin}} = \frac{E_{\text{thin}}[\text{both}]}{E_{\text{thin}}[\text{either}]}$$
  Store `random_thinning_expected_rate` ($C_{\text{thin}}$) and `excess_spatial_drop` ($C_{\text{thin}} - C_{\text{observed}}$) on every audit result.
  * For a true boundary-leakage artifact (like `UMOD` in B-cells bordering thick ascending limb tubules), $C_{\text{observed}}$ drops far below $C_{\text{thin}}$ (`excess_spatial_drop >> 0`).
  * For an intracellularly distributed signal (like `LRP2`/`CUBN` in the hero podocytes), $C_{\text{observed}} \approx C_{\text{thin}}$.
  * **Impact:** This takes 2 milliseconds to compute, requires zero Monte Carlo loops, and gives us an airtight scientific metric that separates true boundary leakage from molecule dropout!

### 2.5 Reviewer Point #6: Lightweight Persisted State on `modal.Volume` for [Modal's 150s Timeout](https://modal.com/docs/guide/webhook-timeouts) & Honest Replay Modes

* **How to Implement in <50 Lines (Tickets 01, 03, 04, 09):**
  1. Persist every investigation to disk (a mounted `modal.Volume` in production, `data/investigations/{inv_id}/` locally): `state.json` (status, approved plan hash, run mode) and `events.jsonl` (one canonical `InvestigationEvent` JSON per line with monotonic `seq: int` and original `recorded_at_utc`).
  2. Make `POST /api/investigations/{inv_id}/approve` idempotent (if `state.status != "awaiting_approval"`, return current status without re-triggering execution) and spawn the orchestrator asynchronously while `GET /api/investigations/{inv_id}/events?after_seq=k` tails `events.jsonl` over [Modal streaming endpoints](https://modal.com/docs/guide/streaming-endpoints). If a client disconnects or hits the 150s boundary, reconnecting with `after_seq` resumes seamlessly without losing a single event.
  3. Explicitly label the three run modes in `InvestigationState.run_mode`:
     * `immutable_replay`: Streams recorded `events.jsonl` verbatim, preserving original `recorded_at_utc` timestamps.
     * `cached_tool_rerun`: Re-executes deterministic Python tools against current data artifacts while serving content-addressed cached model responses (keyed by `sha256(provider + model + messages + schema_version + tool_version + artifact_checksum)`).
     * `live`: Executes live model calls under a file-locked daily budget reservation.

## 3. Four High-Impact Agentic Upgrades That Make Judges Pick SpatialScout

Implement these four enhancements directly inside Tickets 05, 09, 10, and 12. They require **no new external dependencies** and strictly obey `ADR-0001` (100% computed from real artifacts), but they transform the user experience from "a table with a chatbot" into **an autonomous multimodal AI scientist**.

### Upgrade 1: Turn Confounder Checks Into an Autonomous `Muse Spark 1.3` Follow-Up Reflex (Ticket 09)

Instead of computing the random-thinning expectation and the label-sensitivity check silently inside the initial audit call, expose them as explicit deterministic MCP/tool operations (`run_random_thinning_control` and `run_label_sensitivity_check`) in the tool registry!
* **How it works in the Agent Loop (Ticket 09):**
  1. `Muse Wonder` plans the initial assignment audit across `default`, `nucleus_only`, `distance_1um`, and `distance_2um`.
  2. When the initial audit returns, `Muse Spark 1.3` inspects the observation (e.g., "`UMOD` in B-cells dropped from Default to Nucleus-Only, while `LRP2`/`CUBN` in podocytes persisted, but molecule retention fell to ~40%") and **autonomously invokes follow-up tool calls** within its 12-call budget:
     * Calls `run_random_thinning_control` to check whether the co-expression drop exceeds uniform random molecule loss ($C_{\text{thin}} - C_{\text{observed}}$).
     * Calls `run_label_sensitivity_check` to verify whether `LRP2`/`CUBN` persistence depends on how proximal-tubule markers were weighted in the cell-label rule.
* **Why This Wins the Hackathon:** On screen, judges watch `Muse Spark 1.3` act like a senior principal investigator—spotting a potential statistical confounder in the initial tool output and autonomously choosing the exact follow-up control experiment to rule it out!

### Upgrade 2: Dual-Panel Multimodal Vision Verification — `Muse Spark 1.3` Audits Both the Statistical Chart AND the Spatial Tissue Crop (Ticket 10)

Right now, Ticket 10 sends only a 1D per-section dot chart (`figure_id`) to `Muse Spark 1.3` for visual verification. That underutilizes `Muse Spark 1.3`'s multimodal vision and ignores the spatial tissue evidence!
* **How to Upgrade the Figure Renderer & Vision Check (Ticket 06 / 10):**
  Render every finding figure (`figure_id`) as a **2-panel composite PNG**:
  * **Left Panel ( Quantitative Across Sections ):** The clean per-section dot plot + mean bar across conditions (`Default`, `Nucleus-Only`, `1 µm`, `2 µm`, and `SAM 3.1 Exploratory`) with `group (n=k)` labels.
  * **Right Panel ( Spatial Tissue Evidence Crop ):** A 300×300 µm high-contrast crop centered on the highest-contributing cell cluster from the RegionView, plotting cell nuclei coloured by type, the cyan `SAM 3.1` glomerulus outline, retained molecules in solid colour, and **excluded molecules highlighted in bright yellow** in the cytoplasmic expansion zone.
* **Prompt `Muse Spark 1.3` Vision to Return Structured Verification on Both Panels:**
  1. `panel_a_direction_agrees`: Does the plotted condition trend or group comparison match the claim's cited numbers?
  2. `panel_a_outlier_driven`: Is the shift driven by a single section dot?
  3. `panel_b_spatial_pattern`: Do the yellow excluded molecules in the tissue crop cluster along cell-type boundaries / outside the nucleus halo, visually confirming boundary admixture?
* **Why This Wins the Hackathon:** No other team in the competition will have `Muse Spark 1.3` visually cross-checking a statistical plot against a sub-cellular spatial transcriptomics tissue map in a single multimodal verification step.

### Upgrade 3: Interactive "Challenge the Verifier (Inject Error)" Mode in the Public Replay UI (Ticket 10 & Ticket 12)

Ticket 10 already requires building an deterministic `ErrorInjector` that creates 5 kinds of corrupted claims from real claims (`reversed_direction`, `wrong_section_count`, `wrong_dataset_ref`, `changed_effect`, `figure_label_mismatch`) and recording the verifier's results across a benchmark of $\ge 20$ valid and $\ge 20$ injected claims.
* **How to Expose This for Maximum Judge Impact (Ticket 10 / 12 UI):**
  Do not bury the 5 error kinds in a static README table! On every Claim Card in the UI, add an interactive **"Challenge Verifier: Inject Error"** dropdown populated from the pre-recorded benchmark fixture for that claim:
  * `Original Claim (Verified)`
  * `Inject: Swap Direction (Numerical + Visual Fail)`
  * `Inject: Inflate Effect Size by +1.5 log2FC (Independent Recompute Fail)`
  * `Inject: Wrong Section Count n=12 vs n=6 (Structural + Visual Fail)`
  * `Inject: Mismatched Figure ID (Muse Spark 1.3 Vision Disputed)`
* When a judge selects any injected error in the public replay URL, the UI swaps in that pre-recorded corrupted claim + verification result in <100ms (zero live API cost!), showing the exact diff that the independent recompute and `Muse Spark 1.3` vision caught, and flips the status badge to `FAILED (BLOCKED FROM SUMMARY)` or `DISPUTED`.

### Upgrade 4: Instant "Fly-to-Evidence" With Pre-Ranked High-Admixture Cell Clusters (Ticket 05 & Ticket 06)

When a user or judge clicks any row in the Findings table (e.g., `LRP2`/`CUBN` in Podocytes or `UMOD` in B-cells), the `deck.gl` viewer shouldn't just load a 300,000-molecule section zoomed out where everything looks like noise.
* **How to Implement Cleanly (Ticket 05):**
  In the Ticket 05 audit output, compute and store `top_evidence_regions: list[BoundingBox]` per finding—ranking 150×150 µm spatial windows by the count of target-gene molecules affected (or retained) in the target cell type.
* Clicking a finding smoothly animates (`FlyToInterpolator` in `deck.gl`, 800ms duration) directly into the #1 ranked 150×150 µm tissue window with the gene filter automatically locked to the finding's gene pair and yellow excluded molecules toggled ON.

## 4. Summary of Concrete Edits to Apply to `docs/spec/tickets-draft.md` Now

1. **Ticket 01 (`Walking skeleton`):** Update `Finding` contract to the discriminated union `DescriptiveAuditResult | DiseaseContrastFinding`; persist investigation events to `events.jsonl` with monotonic `seq` numbers and explicit `run_mode` (`immutable_replay | cached_tool_rerun | live`).
2. **Ticket 02 (`Dataset store`):** Exclude `LRP2` and `CUBN` from the `Podocyte` positive/negative assignment rule so the hero podocyte population has zero circularity by construction; log the label-sensitivity comparison count in the manifest/audit.
3. **Ticket 05 (`Assignment audit`):** Add the 10-line vectorized NumPy closed-form `random_thinning_expected_rate` ($C_{\text{thin}}$) and `excess_spatial_drop` ($C_{\text{thin}} - C_{\text{observed}}$); include `top_evidence_regions` bounding boxes for instant `deck.gl` fly-to-region.
4. **Ticket 06 (`Findings with evidence labels`):** Apply count gates and leave-one-section-out across **all valid primary conditions**; render the 2-panel composite figure (Panel A: section dot plot; Panel B: 300×300 µm spatial tissue crop with yellow excluded molecules).
5. **Ticket 07 (`SAM 3.1 outlines`):** Badged in UI and contracts as `structure_constrained_exploratory` (`SAM 3.1 Proposal (Exploratory)`) with seed-box coverage, retention, and `PECAM1`/`PDGFRB` consistency; remove as a hard blocker on Tickets 09–11.
6. **Ticket 09 (`Agent loop`):** Split dependencies so `09` starts immediately after `03` and `05` on `DescriptiveAuditResult` (`09a`) and integrates `DiseaseContrastFinding` (`09b`) when `06` completes; expose `run_random_thinning_control` and `run_label_sensitivity_check` as follow-up tools that `Muse Spark 1.3` autonomously calls after inspecting the initial audit.
7. **Ticket 10 (`Verification & benchmark`):** Have `Muse Spark 1.3` inspect both Panel A and Panel B of the composite figure; wire the 5 recorded `ErrorInjector` perturbations per hero claim into an interactive **"Challenge Verifier: Inject Error"** selector on the UI Claim Card.
