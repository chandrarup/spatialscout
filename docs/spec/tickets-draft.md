# SpatialScout tickets: draft for validation

> Not yet published. After you validate this file, each ticket becomes one GitHub issue in dependency order, with native "blocked by" edges, labelled `ready-for-agent` unless marked otherwise. Vocabulary follows `GLOSSARY.md`; the spec is `docs/spec/spec.md`.
>
> To change a ticket, edit it here or leave a note under it. Delete a ticket to drop it.

## Overview

| # | Ticket | Blocked by | Label |
| --- | --- | --- | --- |
| 01 | Walking skeleton on replay | None | ready-for-agent |
| 02 | Real dataset store and capability report | 01 | ready-for-agent |
| 03 | Model gateway with cache, replay, budget and telemetry | 01 | ready-for-agent |
| 04 | Public deployment on Modal | 01 | ready-for-agent |
| 05 | Assignment audit in the split viewer | 02 | ready-for-agent |
| 06 | Findings with evidence labels | 05 | ready-for-agent |
| 07 | Structure outlines from SAM 3.1 | 03, 05 | ready-for-agent |
| 08 | Voice question with editable transcript | 03 | ready-for-agent |
| 09 | Agent loop: plan, approve, execute, draft claims | 03, 06 | ready-for-agent |
| 10 | Verification, injected errors and benchmark | 09 | ready-for-agent |
| 11 | Review decisions and evidence package | 10 | ready-for-agent |
| 12 | Golden path recording, README and demo script | 04, 07, 08, 11 | ready-for-agent |
| 13 | Researcher feedback session | 04, 11 | ready-for-human |
| 14 | Stretch: Muse Glimmer LoRA cell type annotator, evaluated offline | 02 (start only after 12) | ready-for-agent |

Critical path: 01 → 02 → 05 → 06 → 09 → 10 → 11 → 12. After 01, tickets 02, 03 and 04 can run in parallel; after 05, tickets 06 and 07 can.

---

## 01: Walking skeleton on replay

### What to build

The thinnest complete path through every layer, running entirely on recorded model responses. A researcher opens the web app and sees a tiny synthetic section: a few hundred molecules, a dozen cells with cell type labels, and one glomerulus outline. They type a question and see a recorded plan, which they approve. They watch investigation events stream while one tool (an audit of the synthetic section) runs. One claim card appears with its cited numbers and its three statuses, and they download an evidence package. Along the way, this ticket establishes:

- the data contracts as Pydantic models, with TypeScript types generated from them
- the Python package and the web app (React, TypeScript, Vite, Tailwind, deck.gl)
- the model gateway interface, with a replay source only (live sources arrive in 03)
- the append-only, hash-linked audit log
- the seam-2 test harness
- the build, run and test commands in CLAUDE.md

### Acceptance criteria

- [ ] One command starts the API serving the built web app; another runs the web dev server with hot reload. Both are documented in CLAUDE.md.
- [ ] Pydantic models exist for the spec's key contracts. One command generates TypeScript types from them, and the web app compiles against those types.
- [ ] A committed synthetic section fixture has answers known by construction: nuclear and non-nuclear molecules, labelled cells, and one glomerulus outline.
- [ ] Posting a question streams, over SSE, plan proposed → plan approved → tool started → tool finished → claim drafted → package ready, from a recorded-response fixture with no network.
- [ ] The viewer renders the synthetic section's molecules, nuclei and glomerulus outline with deck.gl, and pan and zoom work.
- [ ] The claim card shows the claim text, the cited numbers, and its evidence, verification and review statuses.
- [ ] Export returns a zip with the claims, the audit log and a manifest. The audit log chain check passes, and editing any entry makes it fail.
- [ ] A seam-2 test drives question → package and the chain check through FastAPI's test client.
- [ ] A replay banner labels the run as a replay and shows its recording time.

### Blocked by

None (can start immediately).

---

## 02: Real dataset store and capability report

### What to build

Load all 22 GSE286184 sections into validated molecule and cell tables. Write a dataset manifest covering source URLs, download date, file checksums, panel, section-to-group mapping and coordinate units. The manifest also carries the caveat that 22 sections come from 19 donors with no published mapping.

Write a capability report. Supported: coordinate inspection, assignment audit from molecule flags, and the disease contrast by section. Unavailable, each with its reason: cell and nucleus boundaries, images, deposited cell type labels, and the donor mapping.

Assign frozen cell type labels with the marker rule from the science spike, using default counts and gene scales pooled from the control sections. The viewer can open any real section whole, with molecules coloured by gene and nuclei by cell type label.

### Acceptance criteria

- [ ] One command downloads any missing files and ingests all 22 sections. Reruns are idempotent, and raw data stays out of git.
- [ ] Validation reports unmatched records (for example, molecules whose cell is missing from the cells table) rather than dropping them silently. The quality and panel filters are recorded in the manifest.
- [ ] The manifest and capability report match the contracts and can be viewed in the UI before any plan is proposed.
- [ ] Cell type labels are deterministic and frozen, and label counts are reported per section.
- [ ] The viewer renders a whole section (about 300k molecules) smoothly, with a section picker and a gene filter.
- [ ] Seam-1 tests cover the label rule on a hand-built table and validation catching a malformed input.

### Blocked by

- 01

---

## 03: Model gateway with cache, replay, budget and telemetry

### What to build

One client for every model call:

- **Meta Model API:** chat completions and responses for Muse Wonder and Muse Spark 1.3; responses parsed with `meta-sam-parser` for SAM 3.1; ASR for Muse Voice Transcribe.
- **Baseten and Fireworks:** Muse Spark Open, with failover from Baseten to Fireworks.

The gateway provides:

- a content-hash cache
- live, record and replay sources
- Pydantic validation of every structured output, retried once on a schema failure
- live mode behind a passcode, with a daily spend budget enforced on the server
- telemetry for every call (provider, model, purpose, latency, tokens, estimated cost, cache status), streamed as events and shown as per-provider pills in the UI

### Acceptance criteria

- [ ] A smoke command makes one tiny live call per provider and model and records it. Run in replay mode, the same command makes no network calls and returns identical results.
- [ ] Identical requests hit the cache, and the audit log marks each model response as live or replayed.
- [ ] Live mode is refused without the passcode and refused once the daily budget is spent (seam-2 test with a fake price).
- [ ] A forced Baseten failure falls over to Fireworks for open-weights calls.
- [ ] Reasoning-model defaults (generous max tokens, low reasoning effort) are applied. Empty content with a `length` finish reason is reported as an error, never parsed.
- [ ] During an investigation, the telemetry pills show calls per provider and their cache status.
- [ ] Keys are read only from the backend environment and never reach the browser or the logs.

### Blocked by

- 01

---

## 04: Public deployment on Modal

### What to build

Deploy the single FastAPI app, which also serves the built web app, on Modal (ADR-0004). Secrets come from a Modal Secret, replay is the default and live mode is gated. Redeploying takes one command. Add a Modal batch job that runs the per-section tool across all 22 sections with `.map()`; it starts as the skeleton's tool, and later tickets reuse it.

### Acceptance criteria

- [ ] A public URL serves the walking skeleton's replay end to end.
- [ ] Redeploying is one command, documented in CLAUDE.md.
- [ ] Secrets come only from Modal; nothing secret is in the image or the repo.
- [ ] Every request finishes well inside Modal's 150-second web limit, and long work streams over SSE.
- [ ] The batch job fans out across sections, writes per-section outputs, and logs its runtime and cost.

### Blocked by

- 01

---

## 05: Assignment audit in the split viewer

### What to build

Compute assignment conditions per molecule: default, nucleus-only, and distance caps of 1 and 2 µm. For each section and cell type, report:

- retention
- a co-expression score over frozen exclusive marker pairs, with its coverage and the number of eligible pairs. The pairs come from the single-nucleus reference or a development section and are frozen before evaluation.
- excluded-molecule bits per molecule, carried in the region view

The viewer gains a split slider and a side-by-side mode comparing default with the selected condition. Excluded molecules show in yellow, and a retention badge sits beside every audit number.

### Acceptance criteria

- [ ] Seam-1 tests on hand-built tables:
  - nucleus-only excludes a molecule in a cell's expansion zone
  - retention and co-expression scores match hand calculations
  - a zero-denominator pair is excluded and counted
- [ ] The marker-pair choice is recorded with its source and frozen before the audit runs.
- [ ] The audit tool returns metrics per section × cell type × condition, plus region references for the most affected cells.
- [ ] The split view shows excluded molecules for the chosen condition, with retention beside every number; no audit number appears without retention.
- [ ] A condition that cannot be computed is reported as unavailable, with its reason.

### Blocked by

- 02

---

## 06: Findings with evidence labels

### What to build

Compute findings for DKD vs Control, and for IgAN, MCD and MN vs Control where the gates pass:

- pseudobulk counts per section × cell type × condition
- PyDESeq2 effects with intervals, with shrunken estimates labelled as such
- count gates and leave-one-section-out
- evidence labels by the spec's frozen rules
- a figure per finding using the design that passed the vision spike: one point per section, a mean bar, and `group (n=k)` labels

In the UI, a findings table filters by label, cell type and gene, and clicking a finding flies the viewer to an evidence region.

### Acceptance criteria

- [ ] Seam-1 tests:
  - pseudobulk sums are correct
  - a count-gate failure gives insufficient evidence
  - a reversal gives segmentation-sensitive
  - a consistent effect gives stable
  - a direction flip under leave-one-section-out gives insufficient evidence
  - missing p-values stay null with a reason
- [ ] The frozen rules (gate thresholds, the 0.5 range, the conditions) are recorded in the run configuration and in the findings artifact.
- [ ] Wherever section counts appear, the 22-sections-from-19-donors caveat is disclosed.
- [ ] The pipeline computes and labels the podocyte LRP2/CUBN finding, whatever the label turns out to be.
- [ ] The findings table filters work, and click-to-region works for at least the podocyte finding and one segmentation-sensitive finding.
- [ ] A batch command regenerates every findings table. The outputs are committed as small artifacts with the GEO citation.

### Blocked by

- 05

---

## 07: Structure outlines from SAM 3.1

### What to build

Find glomerulus outlines with SAM 3.1 (ADR-0005):

1. Render a gene-agnostic image of each section from nucleus positions and sizes.
2. Seed one box per glomerulus from merged NPHS1 molecule clusters.
3. Send the boxes to SAM 3.1 as box prompts.
4. Convert the box-local masks into outlines in section coordinates.
5. Report PECAM1 and PDGFRB consistency for each outline.

Outlines and the SAM responses are stored as artifacts. A structure-constrained condition joins the audit and findings: a molecule is excluded when a glomerulus outline separates it from its cell's centroid. The viewer shows the outlines in cyan.

### Acceptance criteria

- [ ] Outlines exist for every glomerulus seed in at least the demo sections, with tuft-gene enrichment reported per outline. NPHS1 is never used to validate an outline.
- [ ] A seam-1 test checks mask placement on a synthetic image with known object positions, using a recorded SAM response.
- [ ] The structure-constrained condition runs through the audit and findings like every other condition.
- [ ] Outlines render in the viewer, labelled as SAM 3.1 proposals.
- [ ] The number of images sent to SAM (and so the cost) is logged.

### Blocked by

- 03
- 05

---

## 08: Voice question with editable transcript

### What to build

Add push-to-talk to the question bar. The browser records audio and encodes 16-bit mono WAV at 16 kHz. The backend sends it through the gateway to Muse Voice Transcribe, biased toward panel gene names where the API supports keywords. The transcript appears in an editable field and must be confirmed before it starts an investigation.

### Acceptance criteria

- [ ] Holding the mic button records; releasing it sends WAV; the transcript appears in an editable field within a few seconds.
- [ ] Nothing runs until the researcher confirms the transcript.
- [ ] A recorded test clip transcribes in replay mode with no network.
- [ ] Errors (no microphone permission, a clip that is too long, an API failure) show a clear message and fall back to typing.

### Blocked by

- 03

---

## 09: Agent loop: plan, approve, execute, draft claims

### What to build

The real investigation orchestrator:

1. Muse Wonder proposes a schema-constrained plan from the question, the capability report and the tool registry.
2. The plan is checked against the registry and the capability report. On failure it re-plans once.
3. The researcher approves the plan, and the deterministic tools run.
4. Muse Spark 1.3 may request follow-up tool calls that cite an observation, within a 12-call budget. A follow-up that changes the contrast becomes a separate exploratory branch.
5. Muse Spark Open on Baseten drafts one claim per selected finding, in parallel, citing only numbers from the artifacts.

The UI shows the capability report, a plan stepper with approve and reject, live events, and claim cards as they are drafted.

### Acceptance criteria

- [ ] A plan naming an unsupported tool or analysis is rejected and re-planned once; if it still fails, the investigation reports the limitation.
- [ ] Nothing executes before plan approval, and the approved plan is frozen in the audit log.
- [ ] Exhausting the budget returns the completed evidence plus open questions.
- [ ] Claims are drafted in parallel and validated against the contract, and tool-call arguments are validated before execution.
- [ ] Seam-2 tests with recorded responses cover the full event sequence for the hero question, an unsupported-plan case, and a budget-exhaustion case.
- [ ] A live run of the hero question completes in under 150 seconds.

### Blocked by

- 03
- 06

---

## 10: Verification, injected errors and benchmark

### What to build

Three checks run on every claim:

- structural checks
- numerical checks: an independent recompute from the stored molecules, within declared tolerances
- visual checks: Muse Spark 1.3 reads the claim's figure

Each claim ends verified, failed, disputed or unavailable, under the spec's blocking rules.

An error injector derives labelled injected errors from real claims. Kinds: reversed direction, wrong section count, wrong dataset reference, changed effect, and figure-label mismatch.

A benchmark of at least 20 valid and 20 injected claims, with a held-out subset, reports detection and false-rejection rates by error kind and by check. The results are committed as a table.

In the UI, a verification card shows the figure and the vision model's critique, and injected errors always carry a badge.

### Acceptance criteria

- [ ] Seam-1 tests: on hand-built data the independent recompute matches the engine and catches each deterministic injected-error kind.
- [ ] Blocking rules:
  - a numerical or structural failure blocks a claim from the validated summary but keeps it in history
  - visual disagreement marks it disputed
  - a correction creates a new claim version
- [ ] The benchmark runs with one command, is replayable, and reports counts by error kind. Its results are committed.
- [ ] One injected error in the golden path is caught on screen and labelled as injected.
- [ ] A seam-2 test shows an injected error ending failed or disputed, with the reason in both the event stream and the audit log.

### Blocked by

- 09

---

## 11: Review decisions and evidence package

### What to build

The researcher records a review decision on each claim (accept for follow-up, needs investigation, or unresolved), by click or by voice with confirmation. Each decision goes into the audit log.

Export produces the evidence package:

- claims with all their statuses
- findings and figures
- the audit log
- a replay manifest and instructions for a full rerun from raw data
- a generated notebook that re-runs the numerical verification from the exported artifacts

A work-in-progress export shows its review state.

### Acceptance criteria

- [ ] Each review decision is recorded with the reviewer, the time and the claim version. Voice decisions need confirmation.
- [ ] The exported notebook runs top to bottom in a clean environment, using only the package, and reproduces the numerical checks.
- [ ] The package states whether its model responses were live or replayed.
- [ ] A seam-2 test checks the export's contents and the chain verification after a review decision.

### Blocked by

- 10

---

## 12: Golden path recording, README and demo script

### What to build

Record one live investigation of the hero question, end to end, and make it the public URL's default replay. Then add:

- a Playwright smoke run against the deployed replay
- a README that separates implemented features from the roadmap. It reports only measured numbers: audit metrics, label counts, benchmark rates, and latency and cost from the logs. It credits the datasets and methods, and states the limitations: donor mapping, panel size, research use only.
- a timed demo-video script built from the recorded run's actual outputs

### Acceptance criteria

- [ ] The public URL plays the recorded investigation start to finish in under three minutes, labelled as a replay with its recording time.
- [ ] The Playwright smoke run passes against the public URL.
- [ ] Every number in the README traces to a committed artifact or a log.
- [ ] The README includes lab-validation results only if ticket 13 produced consented results.
- [ ] The demo script's timings match the recorded run.

### Blocked by

- 04
- 07
- 08
- 11

---

## 13: Researcher feedback session (ready-for-human)

### What to build

Run one session with a researcher on the public URL. Prepare:

- a short task sheet, for example: "Find a DKD finding that survives the audit and one that does not; decide which deserves follow-up"
- a rating form: each claim rated supported, plausible, unsupported or unassessable, plus the time taken, one requested improvement, and consent for quotes

Record the results with consent and triage the top requested improvement. This needs you: scheduling, consent and running the session.

### Acceptance criteria

- [ ] The task sheet and rating form exist and take under 20 minutes to complete.
- [ ] Observed timings and ratings are recorded with consent, and no unpublished data is used.
- [ ] Quotes are used only with permission and never imply institutional endorsement.

### Blocked by

- 04
- 11

---

## 14: Stretch: Muse Glimmer LoRA cell type annotator, evaluated offline

### What to build

Train a Fireworks LoRA on Muse Glimmer 30B that maps a cell's panel-marker profile to a cell type plus the marker evidence behind it. Evaluate it offline on held-out sections against the base model and the frozen marker rule. Record its outputs during a short deployment, then delete the deployment. Show the comparison as an optional panel. Start only after ticket 12 ships.

### Acceptance criteria

- [ ] Training data comes from the frozen labels, with a section-level split.
- [ ] The offline evaluation reports agreement with the marker rule and with the base model, with counts.
- [ ] Any deployment used for recording is deleted afterwards, and its cost is logged.

### Blocked by

- 02 (scheduled after 12)
