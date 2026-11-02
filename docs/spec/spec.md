# Spec: SpatialScout hackathon build (draft for validation)


> Spec for the Meta Global AI Developer Hackathon build (submissions due Nov 4 2026, 9:00 PM ET). Vocabulary follows `GLOSSARY.md`; decisions follow `docs/adr/0001`–`0005`; facts come from `docs/research/` (provider smoke tests, data readiness, spikes). Sources it reconciles: `spatialscout_prd_srs_spec.md` (demo choreography, partner integrations) and `docs/product/build-whitepaper-v2.md` (scientific contracts, which win on conflict).

## Problem Statement

A kidney researcher looking at a spatial-transcriptomics atlas wants to know which disease-vs-control differences deserve months of follow-up. Every one of those differences depends on how the instrument assigned RNA molecules to cells, and assignment errors can manufacture or hide a "disease signature" (Mitchel et al., Nature Genetics 2026). Today the researcher either trusts the default assignment or writes one-off scripts to probe it. There is no workspace where they can ask a question, see whether the answer changes when the assignment rule changes, check that the claims written about it are numerically and visually right, and hand a reproducible record to their PI.

The judges of the Meta hackathon need to see this working on real data within a few minutes, from a public URL that keeps working during judging (Nov 4–8) even when model credits run out.

## Solution

SpatialScout is a web workspace backed by an agent built on Meta's models. The researcher asks a question by typing or speaking ("Do podocytes in DKD really express tubular endocytosis genes, or is that segmentation?"). Muse Wonder reads the dataset's capability report and proposes a plan restricted to supported tools; the researcher approves it. Deterministic tools run the assignment audit across conditions (default, nucleus-only, distance cap, structure-constrained), compute findings per section, and label each one stable, segmentation-sensitive or insufficient evidence. SAM 3.1 delineates glomeruli on an image rendered from the RNA itself, so the structure-constrained condition and the viewer can use them.

A split-screen viewer shows a real GSE286184 section at full resolution: every molecule as a point, cells and glomeruli outlined, and the molecules a stricter condition excludes lit up in yellow, with retention shown beside every number. Claims are drafted in parallel by Muse Spark Open on Baseten, then verified: numbers are recomputed by an independent path, and Muse Spark 1.3 reads each claim's figure to check direction and counts. A clearly labelled injected error is caught on screen. The researcher records a review decision and exports an evidence package (claims, figures, hash-linked audit log, notebook and replay instructions). The public URL plays a labelled replay of a recorded live investigation; live mode is gated.

The hero question is real and citable: the GSE286184 authors reclassified podocytes co-expressing LRP2/CUBN as a new "Podocyte endocytosis" state. In the spike that signal survived nucleus-only assignment, while a few other findings (for example UMOD in B cells) were segmentation-sensitive and most podocyte-level comparisons had insufficient evidence. The demo tells whatever story the final pipeline computes.

## User Stories

### Asking and planning
1. As a researcher, I want to type a question about a gene, cell type and disease, so that I can start an investigation without writing code.
2. As a researcher, I want to hold a button and speak my question, so that I can ask while my hands are busy at the bench.
3. As a researcher, I want to see and edit the transcript of what I said before it is used, so that a misheard gene name never drives an analysis.
4. As a researcher, I want one-click example questions, so that I can see what SpatialScout can answer on this dataset.
5. As a researcher, I want to see the dataset's capability report before a plan is proposed, so that I know which analyses are supported, failed or unavailable and why.
6. As a researcher, I want the planner to propose only steps the capability report supports, so that I am never shown an analysis the data cannot back.
7. As a researcher, I want the plan to state the contrast, cell types, assignment conditions, tools and budget, so that I know exactly what will run.
8. As a researcher, I want to approve or reject the plan, so that nothing runs without my go-ahead.
9. As a researcher, I want an approved plan to be frozen, so that later follow-ups cannot silently change the primary analysis.
10. As a researcher, I want follow-up steps that change the contrast to be recorded as a separate exploratory branch, so that adaptive analysis is never mistaken for the pre-specified one.
11. As a researcher, I want the investigation to stop at its tool-call budget and return what it has plus open questions, so that the agent cannot run analyses until a favourable result appears.

### Seeing the tissue
12. As a researcher, I want to open a real section and see every molecule as a point coloured by gene, so that I can inspect the raw evidence.
13. As a researcher, I want to see cells as nuclei with their cell type labels, so that I can tell which cell a molecule was assigned to.
14. As a researcher, I want glomeruli outlined on the section, so that I can orient myself in kidney anatomy.
15. As a researcher, I want to compare the default condition with a stricter condition side by side or with a split slider, so that I can see what changes.
16. As a researcher, I want excluded molecules highlighted, so that I can see exactly which molecules a stricter condition drops.
17. As a researcher, I want retention shown next to every audit number, so that dropping molecules never looks like a free improvement.
18. As a researcher, I want to filter the view to a few genes, so that the region I care about is not buried in other molecules.
19. As a researcher, I want to click a finding and have the viewer fly to a region that shows its evidence, so that every number links to tissue.
20. As a researcher, I want pan and zoom to stay smooth on a whole section, so that inspection feels immediate.
21. As a researcher, I want approximate cell outlines labelled as approximations, so that I do not mistake them for measured boundaries.

### Assignment audit
22. As a researcher, I want molecules counted under default, nucleus-only, distance-cap and structure-constrained conditions, so that I can see how sensitive each result is to assignment.
23. As a researcher, I want a co-expression score for frozen exclusive marker pairs per section and cell type, so that I have a proxy for admixture.
24. As a researcher, I want the co-expression score reported with coverage and the number of eligible pairs, so that I can judge how much to trust it.
25. As a researcher, I want cell type labels assigned once and frozen across conditions, so that a changed result is attributable to assignment, not relabelling.
26. As a researcher, I want a per-molecule record of which conditions include it, so that excluded molecules can be traced.
27. As a researcher, I want the structure-constrained condition to exclude molecules that sit on the other side of a glomerulus outline from their cell, so that structures act as hard boundaries.
28. As a researcher, I want a condition that cannot be computed to be reported as unavailable, so that a missing input never counts as evidence against a finding.

### Findings and evidence labels
29. As a researcher, I want findings computed per section and cell type for every contrast the data supports, so that sections, not cells, are the unit of replication.
30. As a researcher, I want each finding's effect, uncertainty and per-section values under every condition, so that I can see the whole picture.
31. As a researcher, I want each finding labelled stable, segmentation-sensitive or insufficient evidence by frozen rules, so that labels are consistent and explainable.
32. As a researcher, I want count gates (molecules and cells per section) applied before labelling, so that sparse comparisons are called insufficient rather than sensitive.
33. As a researcher, I want a leave-one-section-out check, so that no single section can drive a label.
34. As a researcher, I want the limitation that 22 sections come from 19 donors disclosed wherever sections are counted, so that I do not over-read replication.
35. As a researcher, I want significance reported separately from evidence labels, so that "stable" is never confused with "significant" or "true".
36. As a researcher, I want to sort and filter findings by label, cell type and gene, so that I can find the ones that matter.
37. As a researcher, I want to see the published "Podocyte endocytosis" signal audited, so that I can judge a real claim from the dataset's own paper.

### Claims and verification
38. As a researcher, I want the agent to write each claim as a sentence citing its numbers, so that I can read results in plain language.
39. As a researcher, I want claims drafted in parallel, so that many findings are covered quickly.
40. As a researcher, I want every claim to carry separate evidence, verification and review statuses, so that a numerically correct claim is not mistaken for an approved one.
41. As a researcher, I want each claim's numbers recomputed from the stored molecules by an independent path, so that a model cannot invent a number.
42. As a researcher, I want each claim's figure inspected by a vision model for direction and section counts, so that a sentence cannot contradict its plot.
43. As a researcher, I want a claim whose figure disagrees to be marked disputed and opened for review, so that I decide, not the model.
44. As a researcher, I want a claim that fails a numerical or structural check blocked from the validated summary but kept in the history, so that errors are visible but contained.
45. As a researcher, I want corrections to create a new claim version, so that history is never rewritten.
46. As a researcher, I want a labelled injected error demonstrated and caught, so that I can see verification working.
47. As a researcher, I want measured detection and false-rejection rates for verification on a benchmark of valid and injected claims, so that I know how far to trust it.

### Review, audit and export
48. As a PI, I want to accept a claim for follow-up, request more investigation, or leave it unresolved, so that the final decision is mine and recorded.
49. As a PI, I want voice review decisions to require confirmation, so that a stray utterance cannot approve a claim.
50. As a PI, I want every tool call, model call and decision in an append-only, hash-linked audit log, so that edits to the history are detectable.
51. As a PI, I want the audit log to say whether each model response was live or replayed, so that I know what was actually computed today.
52. As a PI, I want to export an evidence package with claims, figures, audit log and a notebook, so that I can reproduce and share the work.
53. As a PI, I want the notebook to re-run the numerical verification from the exported artifacts, so that reproduction does not depend on SpatialScout running.
54. As a PI, I want separate instructions for a full rerun from raw GEO data, so that replay and computational reproducibility are not conflated.
55. As a PI, I want work-in-progress exports to show their review state, so that an unreviewed package is never mistaken for a final one.

### Judges and the public URL
56. As a judge, I want the public URL to play a complete investigation without failing, so that I can evaluate the demo during judging.
57. As a judge, I want replays clearly labelled as replays, with the recording time, so that I know what I am seeing.
58. As a judge, I want live telemetry showing which Meta model and which provider handled each step, so that I can see the Meta tooling at work.
59. As a judge, I want the golden path to finish in under three minutes, so that the demo fits a short video.
60. As a judge, I want a README that separates implemented features from the roadmap and reports measured numbers, so that I can trust what I read.
61. As an operator, I want live mode behind a passcode and a daily spend budget enforced in the backend, so that a public URL cannot run up an uncapped bill.
62. As an operator, I want every model call cached by a content hash of its request, so that repeated runs cost nothing and replay is exact.
63. As an operator, I want a provider failover for open-weights calls, so that a Baseten outage does not break claim drafting.
64. As an operator, I want each model call's provider, model, latency, tokens, estimated cost and cache status recorded, so that cost reporting comes from logs, not promises.
65. As an operator, I want the batch audit across all 22 sections runnable as one command, locally or fanned out on Modal, so that whitepaper tables are regenerated from code.
66. As a developer, I want one source of truth for the data contracts with generated TypeScript types, so that backend and frontend cannot drift.

## Implementation Decisions

### Modules (deep modules, one Python package plus one web app)

- **Dataset store.** Loads GSE286184 sections from raw GEO files into validated columnar tables of molecules and cells, writes a dataset manifest (source URLs, download date, file checksums, panel, section-to-group mapping, donor caveat, coordinate units) and a capability report. Filters molecules to `qv ≥ 20` and panel genes; counts, never silently drops, unmatched records. Interface: load a dataset by id; get its manifest and capability report; get one section's molecules and cells.
- **Analysis engine.** All deterministic science behind a small set of tool operations: assign cell type labels (frozen marker rule, from default counts, pooled gene scales from control sections); compute assignment conditions per molecule; audit a section (retention, co-expression score with coverage, excluded-molecule flags); compute findings for a contrast (pseudobulk per section × cell type × condition, PyDESeq2 effects with intervals, count gates, leave-one-section-out, evidence labels); build a region view; render a finding figure; recompute a claim's numbers by an independent path. Every condition is a molecule subset, so counts stay integers and PyDESeq2 is valid (ADR-0002).
- **Structure finder.** Renders a gene-agnostic image of a section from nucleus positions and sizes; seeds one box per glomerulus from merged NPHS1 molecule clusters; asks SAM 3.1 for masks via box prompts; converts box-local masks to section-coordinate outlines; reports PECAM1/PDGFRB consistency per mask. Stores outlines as artifacts (ADR-0005).
- **Model gateway.** One client for every model call: Meta Model API (chat completions and responses for Muse Wonder and Muse Spark 1.3, responses for SAM 3.1, ASR for Muse Voice Transcribe), Baseten and Fireworks (Muse Spark Open, OpenAI-compatible). Content-hash cache, record and replay sources, budget guard and passcode for live mode, failover from Baseten to Fireworks for open-weights calls, Pydantic validation of every structured output, and a telemetry event per call. Reasoning models need generous `max_tokens` and `reasoning_effort: low` by default (spike finding).
- **Investigation orchestrator.** A bounded state machine: question → capability report → plan (Muse Wonder, schema-constrained, checked against the tool registry and capability report, one re-plan allowed) → plan approval → tool execution (deterministic tools; Muse Spark 1.3 may request follow-up tool calls that cite an observation, within a 12-call budget) → finding selection → parallel claim drafting (Muse Spark Open) → verification → review → export. Emits typed investigation events.
- **Verifier.** Structural checks (schema, dataset and finding references, contrast direction, section counts), numerical checks (independent recompute within declared tolerances), visual checks (Muse Spark 1.3 reads the figure and returns higher group, points per group, single-point dependence). Numerical or structural failure blocks a claim from the validated summary; visual disagreement marks it disputed; an unavailable check stays unavailable. An error injector derives injected errors from real claims (reversed direction, wrong section count, wrong dataset reference, changed effect, figure-label mismatch), always flagged as injected.
- **Audit log.** Append-only entries per investigation; each entry's hash covers its canonical content plus the previous hash; a chain check; live-or-replayed flag per model call. Described as tamper-evident, never tamper-proof.
- **Evidence package exporter.** A zip with claims, findings, figures, audit log, replay manifest, raw-rerun instructions and a generated notebook that re-runs the numerical verification from the exported artifacts.
- **HTTP API.** FastAPI. Start an investigation, approve a plan, stream investigation events over SSE, fetch a region view (columnar, compact), submit a voice clip (WAV) for transcription, record a review decision, export a package, list and play recorded investigations. Serves the built web app (ADR-0004).
- **Web app.** React, TypeScript, Vite, Tailwind, deck.gl. Question bar with push-to-talk and editable transcript; capability report and plan stepper with approve; telemetry pills per provider; split viewer (molecules, nuclei, glomerulus outlines, excluded molecules in yellow, retention badges, gene filter, fly-to-region); findings table with labels; claim cards with verification panel (figure plus the vision critique); review controls; audit log ticker; export button; replay banner.

### Contracts

Pydantic models are the single source of truth; JSON Schema is generated from them and TypeScript types from that. Every artifact has a schema version and an immutable id; changing a parameter produces a new run. Key types: DatasetManifest, CapabilityReport, AssignmentCondition, RegionView, AuditMetrics, Finding (effects per condition, gates, label), Claim, VerificationResult (per check: status, details), Plan and PlanStep, InvestigationEvent (a discriminated union), AuditEntry, ReviewDecision, ModelCallRecord.

Claim shape (from the build whitepaper v2, adjusted by the spikes):

```json
{
  "schema_version": "1.0",
  "claim_id": "clm-…",
  "version": 1,
  "investigation_id": "inv-…",
  "dataset_id": "GSE286184",
  "contrast": {"disease": "DKD", "control": "Control"},
  "cell_type": "Podocyte",
  "gene": "LRP2",
  "text": "…",
  "cited": {"effect_default": 0.0, "effect_by_condition": {"nucleus_only": 0.0}, "n_sections": {"DKD": 6, "Control": 3}},
  "finding_id": "fnd-…",
  "figure_id": "fig-…",
  "evidence_status": "stable | segmentation_sensitive | insufficient_evidence",
  "verification_status": "pending | verified | failed | disputed | unavailable",
  "review_status": "unreviewed | accepted_for_follow_up | needs_investigation | unresolved",
  "injected": {"is_injected": false, "kind": null}
}
```

Missing values stay null with a reason; a missing p-value never becomes zero.

### Frozen analysis rules (primary analysis; sensitivity grid reported separately)

- Primary contrast: DKD (6 sections) vs Control (3 sections). IgAN, MCD and MN vs Control are computed with the same code and shown if they pass gates.
- Conditions: default; nucleus-only; distance caps of 1 µm and 2 µm (non-nuclear molecules within the cap kept); structure-constrained (from glomerulus outlines).
- Count gate: every section needs ≥ 10 molecules of the gene in the cell type and ≥ 20 cells of the type; otherwise insufficient evidence.
- Labels: stable when the direction agrees across valid conditions, the log2 effect range is ≤ 0.5, and leave-one-section-out keeps the direction; segmentation-sensitive on a reversal or range > 0.5; else insufficient evidence. The 0.5 threshold is a design choice, frozen before the primary run.
- Sections are the replication unit. GEO does not map sections to donors (22 sections, 19 donors); this is disclosed in the capability report and the README.
- Exclusive marker pairs are chosen from the single-nucleus reference (GSE271188) or a development section, then frozen before evaluation.

### Model jobs (every model has a real job)

| Model / platform | Job |
| --- | --- |
| Muse Wonder (`muse-wonder-1.0`, Meta API) | Schema-constrained plan limited to the capability report |
| Muse Spark 1.3 (`muse-spark-1.3`, Meta API) | Follow-up tool calls; claim explanations; figure verification by vision |
| SAM 3.1 (`sam-3.1`, Meta API) | Glomerulus outlines from box prompts on RNA-derived images |
| Muse Voice Transcribe (`muse-voice-transcribe-1.0`, Meta API) | Push-to-talk questions and confirmed review decisions |
| Muse Spark Open on Baseten (`meta-models/muse-spark-open`) | Parallel claim drafting per finding |
| Muse Spark Open on Fireworks (`accounts/fireworks/models/muse-spark-open`) | Failover for open-weights calls |
| Modal | Hosting the single deployable; batch audit across 22 sections with `.map()` |

### Specific interactions

- Voice: the browser records PCM and encodes 16-bit mono WAV at 16 kHz itself; the backend forwards it to `/v1/asr/transcribe` (WAV only, per Meta docs). The transcript is editable and must be confirmed.
- Replay: the gateway serves stored responses; the orchestrator re-emits recorded events with their original relative timing, optionally sped up. The replay banner shows the recording time.
- The region view ships molecules as compact columns (positions, gene index, cell index, per-condition inclusion bits), so a whole section (about 300k molecules) renders at once.

## Testing Decisions

- A good test checks behaviour through a public interface with an expected value from an independent source (a hand-built example, a worked calculation), never by re-running the implementation's own logic.
- **Seam 1: the analysis engine's public operations.** Tests use tiny hand-built molecule and cell tables whose answers are known by construction: a molecule in a podocyte's expansion zone excluded by nucleus-only; retention and co-expression scores computed by hand; pseudobulk sums; count gates; label thresholds including a reversal; leave-one-section-out; the independent recompute agreeing with the engine and catching each injected error kind.
- **Seam 2: the HTTP/SSE API.** FastAPI's test client with the model gateway in replay mode over a recorded-response fixture: a question yields the expected event sequence; plan approval gates execution; an injected error ends failed or disputed; the audit log chain verifies; the export contains the expected parts; live mode is refused without the passcode or over budget.
- No UI unit tests. One Playwright smoke run of the replayed golden path against the deployed URL at the end.
- Model quality is measured by the verification benchmark (at least 20 valid and 20 injected claims, a held-out subset), not by unit tests.
- Prior art: none in the repo yet; `spikes/` holds reference computations that seam-1 tests may borrow worked examples from.

## Out of Scope

- Fine-tuning SAM 3.1 (no 3.1 training recipe; gated weights) and SAM tile-video stitching (unverified ID stability across seams).
- Re-segmentation or published correction tools (Proseg, Cellpose-SAM, cellAdmix, 2DE).
- Datasets other than GSE286184: Visium, lupus nephritis, mouse, 10x preview kidney.
- Lupus-nephritis framing; the cohort is DKD, IgAN, MCD and MN.
- A urine-biomarker bridge beyond, at most, one VCAM1 card labelled as a candidate tissue association (VCAM1 is the only Stanley 2020 protein confirmed in the panel).
- Serving a Muse Glimmer LoRA live (an on-demand deployment costs about $8/hour). An offline-evaluated LoRA is a stretch goal only after everything else ships.
- Arbitrary code execution by the agent, multi-user collaboration, accounts.
- Clinical use: outputs are research hypotheses, never diagnoses or patient-level predictions.

## Further Notes

### Demo storyboard (about 2.5 minutes, written from computed outputs)

1. Hook: a 2026 kidney atlas reports "Podocyte endocytosis". Biology, or where the instrument drew the cell edges?
2. The researcher asks by voice; the editable transcript appears; Muse Wonder proposes a plan limited to what the capability report supports; approve.
3. The viewer flies from the whole biopsy strip into a glomerulus outlined by SAM 3.1 from an image made of RNA; the split slider shows default vs nucleus-only, excluded molecules in yellow, retention beside every number.
4. Findings: the podocyte LRP2/CUBN signal labelled with whatever the pipeline computes, a segmentation-sensitive finding clicked to fly to its evidence, and the honest count of insufficient-evidence comparisons.
5. Claims drafted in parallel on Baseten; a labelled injected error caught by Muse Spark 1.3 reading the figure, critique on screen.
6. Review decision, evidence package export, audit log chain verified. Telemetry shows every Meta model and partner used.

### Schedule and human-only steps

- Nov 2: walking skeleton deployed on replay; real-data audit and findings.
- Nov 3: agent loop, verification and benchmark, structure outlines, voice, export; record the golden-path investigation live.
- Nov 4: polish; the user records the demo video late morning; code freeze about 1 PM CT; repo made public; submit by about 5 PM CT; push nothing after 8 PM CT (a repository change after the deadline marks the project late).
- Muse Code was not used to build this; the submission must not claim it.

### Risks

- Model credits lapse during judging: replay by default (ADR-0003).
- Sparse podocyte counts: count gates and insufficient-evidence labels (spike 1).
- Donor mapping unknown: disclosed; leave-one-section-out.
- SAM outlines imperfect: shown as SAM proposals with tuft-gene consistency, used as one named condition, never as validation.
