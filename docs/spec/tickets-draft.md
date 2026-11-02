# SpatialScout tickets: draft for validation (revision 2)

> Not yet published. After you validate this file, each ticket becomes one GitHub issue in dependency order, with native "blocked by" edges, labelled `ready-for-agent` unless marked otherwise. Vocabulary follows `GLOSSARY.md`; the spec is `docs/spec/spec.md`.
>
> Revision 2 adopts Section 4 of `docs/spec/reviews/agent-directive-winning-upgrades.md` and the reviewer's required changes (`docs/spec/reviews/plan-review.md`), with the corrections listed in `docs/spec/review-response.md`.

## Overview

| # | Ticket | Blocked by | Label |
| --- | --- | --- | --- |
| 01 | Walking skeleton on replay, with persisted investigations | None | ready-for-agent |
| 02 | Real dataset store, label rules and capability report | 01 | ready-for-agent |
| 03 | Model gateway with cache, run modes, budget and telemetry | 01 | ready-for-agent |
| 04 | Public deployment on Modal | 01 | ready-for-agent |
| 05 | Assignment audit with thinning controls and evidence regions | 02 | ready-for-agent |
| 06 | Descriptive disease contrasts | 05 | ready-for-agent |
| 07 | SAM 3.1 outlines as an exploratory condition | 03, 05 | ready-for-agent |
| 08 | Voice question with editable transcript | 03 | ready-for-agent |
| 09a | Agent loop on audit results, with agent-chosen controls | 03, 05 | ready-for-agent |
| 09b | Disease contrasts in the agent loop | 06, 09a | ready-for-agent |
| 10 | Verification, injected errors, benchmark and "Challenge the verifier" | 09a | ready-for-agent |
| 11 | Review decisions and evidence package | 10 | ready-for-agent |
| 12 | Golden path recording, README and demo script | 04, 11 | ready-for-agent |
| 13 | Researcher feedback session | 04, 11 (task sheet can start now) | ready-for-human |
| 14 | Stretch: Muse Glimmer LoRA annotator, agreement study | 12 | ready-for-agent |

Delivery stages:

| Stage | Tickets | Exit condition |
| --- | --- | --- |
| Foundation | 01, then 02 / 03 / 04 | Real data visible; gateway usable; public skeleton works |
| First real investigation | 05, 09a, 10, 11 | Ask, audit, inspect, check, review and export on real data |
| Evidence quality | 06, 09b, extended 10 | Descriptive contrasts labelled; benchmark recorded |
| First submission candidate | 12 | Real run recorded, replay tested, every claim traced |
| Enhancements | 07, 08 | Plug into the working app when ready; never gate 12 |
| User value | 13 | Observed feedback informs one improvement |
| Stretch | 14 | Agreement study only after 12 |

Critical path: 01 → 02 → 05 → 09a → 10 → 11 → 12.

---

## 01: Walking skeleton on replay, with persisted investigations

### What to build

The thinnest complete path through every layer, on recorded model responses.

A researcher opens the web app and sees a tiny synthetic section: a few hundred molecules, a dozen cells with cell type labels, and one glomerulus outline. They type a question, see a recorded plan and approve it. They then watch investigation events stream while one tool runs (an audit of the synthetic section). One claim card appears, citing an audit result, and they download an evidence package.

Investigations persist on disk, independent of any HTTP connection, so a refresh or reconnect never loses events.

The ticket also establishes:

- the data contracts: Pydantic models with generated TypeScript types, including the finding union below
- the Python package and the web app (React, TypeScript, Vite, Tailwind, deck.gl)
- the model gateway interface, with a replay source only
- the append-only, hash-linked audit log
- the seam-2 test harness
- the commands in CLAUDE.md

Contract decisions this ticket fixes:

- **Finding** is a discriminated union on `finding_kind`:
  - `audit` (an audit result): per section and assignment condition, it carries the observed value, retention, nuclear-overlap share, both random-thinning expectations (cell-matched and home-matched), excess drop, fixed population counts, label rule id, evidence regions and label.
  - `contrast` (a contrast result): it carries per-section library-size-normalised log2 values, an effect per condition, leave-one-section-out influence, `inference_eligibility` (always `descriptive_only` in this release, with its reason) and label.

  Fields may start shallow but must be typed; tickets 05 and 06 fill them. A claim cites one finding by id and kind.
- **Investigation state**: a directory per investigation containing:
  - `state.json`: status, `run_mode`, approved-plan hash, timestamps
  - `events.jsonl`: one event per line, each with a monotonic integer `seq` and its original `recorded_at_utc`
- **Run mode**: `immutable_replay`, `cached_tool_rerun` or `live`. The replay banner shows the run mode and the recording time.

### Acceptance criteria

- [ ] One command starts the API serving the built web app; another runs the web dev server with hot reload. Both are documented in CLAUDE.md.
- [ ] One command generates TypeScript types from the Pydantic models, and the web app compiles against them.
- [ ] The synthetic section fixture is committed, with answers known by construction. It includes:
  - nuclear and non-nuclear molecules, including one in a cell's expansion zone that nucleus-only excludes
  - labelled cells
  - one glomerulus outline
- [ ] Posting a question creates a persisted investigation. Its events stream over SSE from a recorded-response fixture, with no network: plan proposed → plan approved → tool started → tool finished → claim drafted → package ready.
- [ ] Approval is idempotent: when the status is not `awaiting_approval`, approving returns the current state and starts nothing.
- [ ] The events endpoint takes `after_seq=k` and streams exactly the events with `seq > k`, in order.
- [ ] The viewer renders molecules, nuclei and the outline with deck.gl, and pan and zoom work.
- [ ] The claim card shows the text, the cited numbers and the three statuses.
- [ ] Export returns a zip with the claims, the audit log and a manifest that records the audit log's head hash.
  - The chain check passes.
  - Editing any entry makes it fail.
- [ ] Seam-2 tests through FastAPI's test client cover:
  - question → package
  - refresh at approval
  - duplicate approval, which must not run the plan twice
  - reconnect mid-execution with `after_seq`, which must deliver exactly the missing events
  - the chain check

### Blocked by

None (can start immediately).

---

## 02: Real dataset store, label rules and capability report

### What to build

Load all 22 GSE286184 sections into validated molecule and cell tables. Write the dataset manifest: source URLs, download date, checksums, panel, section-to-group map and units.

Freeze two cell type label rules:

- The **full-panel rule**: the spike's marker rule from default counts, with gene scales pooled from the control sections.
- The **NPHS1-anchored podocyte rule**: it decides podocyte membership without using LRP2 or CUBN, so the population the hero question asks about is not selected on the genes it measures. The panel has no NPHS2, PODXL or WT1, so NPHS1 is the only podocyte marker available.

Neither rule is free of selection bias. The anchored rule can admit proximal-tubule cells carrying stray NPHS1, so the label-sensitivity check in ticket 05 reports both. Per section, record the counts under each rule and the cells whose label differs between them.

The capability report states:

- **Supported:** coordinate inspection, assignment audit from molecule flags, and descriptive disease contrasts by section.
- **Unavailable**, each with its reason: boundaries, images, deposited labels, and donor mapping.
- **Inference eligibility of every contrast:** descriptive only, because 22 sections come from 19 donors with no published mapping. IgAN vs Control is "conditionally donor-distinct by published counts, unconfirmed". Donor identity is never inferred from expression (ADR-0007).

The viewer opens any real section whole.

### Acceptance criteria

- [ ] One command downloads any missing files and ingests all 22 sections. Reruns are idempotent, and raw data stays out of git.
- [ ] Validation counts unmatched records and never drops them silently. The quality and panel filters are recorded in the manifest.
- [ ] The manifest and capability report match the contracts, including per-contrast inference eligibility, and can be viewed in the UI before any plan is proposed.
- [ ] Both label rules are deterministic and frozen. Per-section counts under each rule, and the number of cells whose label differs, are recorded.
- [ ] The viewer renders a whole section (about 300k molecules) smoothly, with a section picker and a gene filter.
- [ ] Seam-1 tests:
  - both label rules on a hand-built table, including a cell whose label differs between the rules
  - validation catching a malformed input

### Blocked by

- 01

---

## 03: Model gateway with cache, run modes, budget and telemetry

### What to build

One client for every model call:

- **Meta Model API**:
  - chat completions and responses for Muse Wonder and Muse Spark 1.3
  - responses parsed with `meta-sam-parser` for SAM 3.1
  - ASR for Muse Voice Transcribe
- **Baseten and Fireworks**: Muse Spark Open, failing over from Baseten to Fireworks.

The gateway provides:

- **Content-addressed cache.** The cache key is a hash of provider, model, inputs, response schema version, tool version and artifact checksum.
- **Run-mode sources:**
  - `immutable_replay` serves recorded events.
  - `cached_tool_rerun` serves stored responses while tools re-execute.
  - `live` makes fresh calls.
- **Local validation of every structured output.** Each output is validated against its Pydantic model, with one bounded repair attempt. Baseten's docs do not promise a JSON mode, and one successful smoke response is not a guarantee.
- **Live-mode gate.** A passcode plus a daily spend budget. Spend is reserved atomically under a file lock before each call and reconciled after it, so parallel drafting cannot overspend.
- **Per-call telemetry**: provider, model, purpose, latency, tokens, estimated cost, cache status and run mode. Each call is streamed as an event and shown as per-provider pills.

### Acceptance criteria

- [ ] A smoke command makes one tiny live call per provider and model and records it. The same command under `cached_tool_rerun` makes no network calls and returns identical results.
- [ ] Changing the tool version or the artifact checksum misses the cache.
- [ ] The audit log marks each model response as live or stored.
- [ ] Live mode is refused without the passcode and once the budget is spent. Concurrent reservations never exceed the budget (seam-2 test with a fake price and parallel calls).
- [ ] A forced Baseten failure falls over to Fireworks.
- [ ] Reasoning-model defaults are applied. Empty content with a `length` finish reason is reported as an error.
- [ ] Keys never reach the browser or the logs.

### Blocked by

- 01

---

## 04: Public deployment on Modal

### What to build

Deploy the single FastAPI app, which also serves the web build, on Modal (ADR-0004):

- **Secrets:** from a Modal Secret.
- **Run modes:** immutable replay is the default; live runs are gated.
- **Investigation state:** kept on a Modal Volume. One web container runs, so the orchestrator and the readers share state.
- **Long investigations:** each SSE connection closes before Modal's 150-second request limit, and the client reconnects with `after_seq`. The orchestrator runs independently of any request.
- **Redeploying:** takes one command.
- **Batch job:** runs per-section tools across all 22 sections with `.map()`.

### Acceptance criteria

- [ ] A public URL serves the skeleton's immutable replay end to end.
- [ ] An investigation longer than 150 seconds streams completely through reconnects, with no lost or duplicated events.
- [ ] Redeploying is one command, documented in CLAUDE.md. Secrets come only from Modal.
- [ ] The batch job fans out across sections and logs its runtime and cost.

### Blocked by

- 01

---

## 05: Assignment audit with thinning controls and evidence regions

### What to build

Compute the four primary assignment conditions per molecule: default, nucleus-only, and distance caps of 1 and 2 µm. Then produce audit results under the spec's frozen rules.

**Populations.** Every population is fixed under the default condition, and all conditions are computed over the same cells. A cell with no retained molecules counts as non-expressing and stays in the denominator. Cells with at least one retained molecule are reported separately.

**Measures**, per section and condition:

- retention and the nuclear-overlap share
- the observed value: the share of the population expressing a gene or gene set, or the co-expression score over the exclusive marker pairs frozen in `configs/exclusive_marker_pairs.json`
- two closed-form random-thinning expectations:
  - **cell-matched**: each cell's own retention, applied to every gene
  - **home-matched**: the gene's retention in its home cell type under the same condition. This is the admixture test, because nuclear fraction varies by gene (UMOD in TAL 0.34 vs NPHS1 in podocytes 0.75 in the spike).

  The hero measure (podocytes with LRP2 or CUBN present) gets its own expectation.
- the excess drop against each expectation
- the **neighbour-proximity share**: the share of excluded molecules closer to a cell of the gene's home type than to their own cell's centroid, reported next to the same share for retained molecules

**Label-sensitivity check.** For the hero population, compare the full-panel and NPHS1-anchored label rules.

**Evidence regions.** Rank 150 × 150 µm windows per finding by the number of the finding's molecules excluded within the population, and record the ranking rule.

**Tools.** Register `run_random_thinning_control` and `run_label_sensitivity_check` as tools of their own, so the agent can choose them (ticket 09a).

**Viewer:**

- Split slider and side-by-side view, default vs the selected condition.
- Excluded molecules in yellow.
- Retention and the home-matched expectation beside every observed number.
- **Fly to evidence**: clicking a finding animates over about 800 ms into its top-ranked region, with the gene filter locked to the finding's genes and excluded molecules shown. The ranking rule is visible, and the user can step through ranks 2, 3 and so on.

**Composite figure.** Each audit result gets a two-panel figure:

- Panel A: per-section observed values against both expectations, across conditions.
- Panel B: a 300 × 300 µm crop of the top evidence region, showing nuclei by cell type, retained molecules, excluded molecules in yellow and, once ticket 07 lands, the exploratory outline.

### Acceptance criteria

- [ ] Seam-1 tests on hand-built tables:
  - Nucleus-only excludes an expansion-zone molecule.
  - Retention and the co-expression score match hand calculations.
  - A zero-retention cell stays in the denominator.
  - Both thinning expectations match worked examples, and a seeded Monte Carlo simulation agrees with the closed form within tolerance.
  - The neighbour-proximity share is correct on a hand-built layout.
  - Evidence-region ranking follows the stated rule.
- [ ] The marker pairs come from the frozen artifact. The artifact's source and checksum are recorded in every audit result.
- [ ] Audit labels follow the spec's frozen rules. No label is asserted in advance, including for the hero population and UMOD in B cells.
- [ ] The label-sensitivity check reports the hero measure under both label rules, with cell counts.
- [ ] Fly to evidence works with rank stepping, and no audit number appears without its retention and expectation.
- [ ] Each audit result renders a composite figure.

### Blocked by

- 02

---

## 06: Descriptive disease contrasts

### What to build

Compute contrast results for DKD, IgAN, MCD and MN vs Control under the four primary conditions. Each result carries:

- per-section library-size-normalised log2 values (the normalisation is frozen and recorded)
- the effect per condition, as a log2 ratio of group means
- leave-one-section-out influence across every valid primary condition
- labels by the frozen rules

There are no p-values or confidence intervals. Every contrast is descriptive only, with its reason (ADR-0007).

Extend the composite figure for contrasts. Panel A shows per-section values by group and condition, with `group (n=k)` labels, plus an exploratory column once ticket 07 lands. Panel B is the tissue crop of the top evidence region.

The UI gains a findings table covering audit and contrast results, filterable by kind, label, cell type and gene, with fly to evidence.

### Acceptance criteria

- [ ] Seam-1 tests:
  - library-size normalisation and the log2 ratio, by hand
  - gate precedence, each case producing the label shown:

    | Case | Label |
    | --- | --- |
    | Population gate fails | insufficient evidence |
    | Molecule gate fails in one condition | that condition is invalid |
    | Fewer than two valid primary conditions | insufficient evidence |

  - label cases: a near-zero effect is never counted as a reversal; a genuine reversal is labelled segmentation-sensitive; a consistent effect is labelled stable; a leave-one-section-out flip in any valid condition is labelled insufficient evidence
- [ ] The frozen rules are recorded in the run configuration and in every result.
- [ ] Every display of section counts carries the 22-sections-from-19-donors disclosure.
- [ ] Representative findings open in the viewer. A segmentation-sensitive finding is shown only if the pipeline produces one.
- [ ] A batch command regenerates every table. The outputs are committed as small artifacts with the GEO citation.

### Blocked by

- 05

---

## 07: SAM 3.1 outlines as an exploratory condition

### What to build

Produce glomerulus outlines, as ADR-0005 describes, with their scope narrowed by ADR-0006:

1. Render a gene-agnostic nucleus image.
2. Seed one box per glomerulus from merged NPHS1 clusters.
3. Send the boxes to SAM 3.1 as box prompts.
4. Convert the box-local masks into section-coordinate outlines.

Each proposal is compared with its seed box and with a geometric baseline, the convex hull of its seed cluster. For each of the three, report area, seed-box coverage, the molecule retention it would cause, and PECAM1/PDGFRB consistency.

Empty, fragmented and rejected proposals are allowed and recorded. Every outline carries a mask version and a run id.

The structure-constrained condition is computed but stays exploratory. It appears in the table, the slider and the figures, badged "SAM 3.1 proposal (exploratory)", and never enters an evidence label.

### Acceptance criteria

- [ ] For each demo section, every seed has an outline or a recorded empty or rejected result, plus the three-way comparison. NPHS1 is never used to validate an outline.
- [ ] A seam-1 test checks mask placement against a recorded SAM response on a synthetic image. It validates coordinates, not anatomy.
- [ ] Adding or removing the exploratory condition changes no evidence label (test).
- [ ] The number of images sent to SAM, and so the cost, is logged.

### Blocked by

- 03
- 05

---

## 08: Voice question with editable transcript

### What to build

Add push-to-talk to the question bar:

- The browser records audio and encodes it as 16-bit mono WAV at 16 kHz.
- The gateway sends it to Muse Voice Transcribe, biased toward panel genes where the API supports keyword biasing.
- The transcript appears editable, and nothing runs until the researcher confirms it.

Voice is an enhancement and never gates ticket 12.

### Acceptance criteria

- [ ] Hold to record, release to send; the transcript appears editable within a few seconds.
- [ ] Nothing runs until the researcher confirms the transcript.
- [ ] A recorded clip transcribes under `cached_tool_rerun` with no network.
- [ ] Errors fall back to typing, with a clear message.

### Blocked by

- 03

---

## 09a: Agent loop on audit results, with agent-chosen controls

### What to build

The investigation orchestrator, running on audit results:

1. **Plan.** Muse Wonder proposes a schema-constrained plan from the question, the capability report and the tool registry. The plan is checked against the registry and the capability report, with one re-plan allowed.
2. **Approve and run.** The researcher approves, and the deterministic audit tools run.
3. **Choose the controls.** Muse Spark 1.3 inspects each tool observation and may request follow-up tools within a 12-call budget, each request citing the observation that motivated it. The follow-ups include `run_random_thinning_control` and `run_label_sensitivity_check`. The orchestrator never runs a control on the agent's behalf. Verification (ticket 10) fails any claim missing a required control, so the agent's choice carries weight.
4. **Draft.** Muse Spark Open on Baseten drafts one claim per selected audit result, in parallel, citing only numbers from the artifacts and using the spec's claim wording.

The UI shows the agent's reasoning as it happens:

- the capability report
- the plan stepper with approve and reject
- each observation, the control the agent chose and why, and that control's result
- claim cards as they are drafted

### Acceptance criteria

- [ ] A plan naming an unsupported tool is rejected and re-planned once; if it fails again, the investigation reports the limitation.
- [ ] Nothing executes before approval, and the approved plan's hash is frozen in the state and the audit log.
- [ ] Each follow-up request records its cited observation, and the UI shows it.
- [ ] Exhausting the budget returns the completed evidence plus open questions.
- [ ] Tool arguments and claims are validated before use.
- [ ] Seam-2 tests with recorded responses cover:
  - the hero question, including the agent's follow-up controls
  - an unsupported plan
  - budget exhaustion
  - a run in which the agent skips a control, which must end with no control run on its behalf

### Blocked by

- 03
- 05

---

## 09b: Disease contrasts in the agent loop

### What to build

Register a `compute_disease_contrast` tool and contrast results in the existing loop. The planner may then propose contrasts, and claims may cite contrast results under the same drafting and verification path.

### Acceptance criteria

- [ ] The planner can schedule a contrast, and the capability report's inference eligibility is shown beside it.
- [ ] Contrast claims pass through the same verifier as audit claims, and the benchmark from ticket 10 includes them.
- [ ] A seam-2 test covers a contrast question end to end.

### Blocked by

- 06
- 09a

---

## 10: Verification, injected errors, benchmark and "Challenge the verifier"

### What to build

Three checks run on every claim:

- **Structural:** schema and references, section counts, and required controls. A claim about assignment sensitivity must cite a home-matched thinning control. A claim about the hero population must cite the label-sensitivity check.
- **Numerical:** an independent code path recomputes every cited number from the stored molecule tables, within declared tolerances.
- **Visual:** Muse Spark 1.3 reads the composite figure and answers three questions:
  - Does Panel A's direction match the claim?
  - Does a single section drive Panel A?
  - Does Panel B show the neighbour pattern the claim states?

  The neighbour-proximity share backs the Panel B answer with a number.

Claims end verified, failed, disputed or unavailable, under the spec's rules.

**Error injector.** It derives labelled injected errors from real claims. Kinds:

- reversed direction
- wrong section count
- wrong dataset reference
- changed effect
- figure-label mismatch
- misstated spatial pattern
- missing required control

**Benchmark.** At least 20 valid and 20 injected claims, with a held-out subset. It reports detection and false-rejection rates by error kind and by check.

**Challenge the verifier.** Every hero claim card gets a "Challenge the verifier" selector. Its options are the claim's recorded injected variants, each named only by its error kind. Choosing one swaps in the recorded variant and its recorded verification within 100 ms, at no model cost. It shows the diff and the actual outcome, including any miss.

### Acceptance criteria

- [ ] Seam-1 tests:
  - the independent recompute matches the engine on hand-built data
  - it catches every deterministic error kind
  - a claim missing a required control fails the structural check
- [ ] Claim states follow these rules:

  | Check result | Claim |
  | --- | --- |
  | Numerical or structural failure | Blocked from the validated summary, kept in history |
  | Visual disagreement | Disputed |
  | Correction | New claim version |

- [ ] The benchmark runs with one command, is replayable, and its results are committed.
- [ ] Selector labels never state expected outcomes; the UI shows only recorded results.
- [ ] One injected error is shown on screen in the golden path and labelled as injected.
- [ ] A seam-2 test shows an injected error ending failed or disputed, with its reason in both the event stream and the audit log.

### Blocked by

- 09a

---

## 11: Review decisions and evidence package

### What to build

The researcher reviews each claim by click (voice confirmation is added if ticket 08 lands): accept for follow-up, needs investigation, or unresolved. Each decision goes into the audit log.

Export produces the evidence package:

- claims with all statuses
- findings and composite figures
- the audit log, and its head hash in the package manifest
- the run mode
- a replay manifest and instructions for a full rerun from raw data
- a generated notebook that re-runs the numerical verification from the exported artifacts

Work-in-progress exports show their review state.

### Acceptance criteria

- [ ] Each decision records the reviewer, the time and the claim version.
- [ ] The notebook runs top to bottom in a clean environment, using only the package, and reproduces the numerical checks.
- [ ] The manifest states the run mode and the head hash.
- [ ] A seam-2 test checks the export's contents and the chain verification after a review.

### Blocked by

- 10

---

## 12: Golden path recording, README and demo script

### What to build

Record one live investigation of the hero question and make it the public URL's default immutable replay. Integrate tickets 07, 08 and 09b if they have landed; this ticket never waits for them.

Then add:

- a Playwright smoke run against the public URL
- a README that:
  - separates implemented features from the roadmap
  - reports only measured numbers
  - credits datasets and methods
  - states the limitations: donor mapping, panel size, descriptive contrasts, exploratory SAM outlines, research use only
- the golden path's audit-log head hash, committed to the repo as an anchor outside the log
- a timed demo-video script built from the recorded run's actual outputs

### Acceptance criteria

- [ ] The public URL plays the recorded investigation in under three minutes, labelled as an immutable replay with its recording time.
- [ ] The Playwright smoke run passes.
- [ ] Every README number traces to a committed artifact or log.
- [ ] The README includes lab-validation results only if ticket 13 produced consented results.
- [ ] The demo script shows whatever the pipeline computed; no finding's outcome is written in advance.

### Blocked by

- 04
- 11

---

## 13: Researcher feedback session (ready-for-human)

### What to build

Run one session with a researcher, using two materials:

- **Task sheet**, for example: "Find a result that holds under the audit and one that does not, or none; decide which deserves follow-up."
- **Rating form**: each claim rated supported, plausible, unsupported or unassessable, plus the time taken, one requested improvement, and consent for quotes.

The task sheet and form can be drafted now. The session itself runs on the public URL once 04 and 11 land. Record the results with consent and triage the top request. This needs you: scheduling, consent and running the session.

### Acceptance criteria

- [ ] The materials take under 20 minutes.
- [ ] Results are recorded with consent, and no unpublished data is used.
- [ ] Quotes are used only with permission and imply no institutional endorsement.

### Blocked by

- 04
- 11

The task sheet and rating form can start now.

---

## 14: Stretch: Muse Glimmer LoRA annotator, agreement study

### What to build

Train a Fireworks LoRA on Muse Glimmer 30B that maps marker profiles to a cell type plus the marker evidence behind it. Evaluate it offline against the frozen rules and the base model, on a split that keeps donor overlap out of evaluation as far as the published counts allow.

Agreement with the marker rule measures imitation, not cell-type accuracy, and is reported as such. Record outputs during a short deployment, then delete it.

### Acceptance criteria

- [ ] The training and evaluation split is section-level and documented.
- [ ] The results are reported as agreement, with counts.
- [ ] The deployment is deleted afterwards, and its cost is logged.

### Blocked by

- 12
