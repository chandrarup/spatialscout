# Spec: SpatialScout hackathon build (revision 2)

> **Published Nov 2 2026 as [#1](https://github.com/chandrarup/spatialscout/issues/1); the issue is canonical for scope.** This file is the snapshot at publication; tickets are its sub-issues, indexed in `docs/spec/tickets.md`.

> Spec for the Meta Global AI Developer Hackathon build (submissions due Nov 4 2026, 9:00 PM ET).
>
> - **Vocabulary** follows `GLOSSARY.md`; **decisions** follow `docs/adr/0001`–`0007`; **facts** come from `docs/research/`.
> - **Revision 2** adopts the agent directive's Section 4 (`docs/spec/reviews/agent-directive-winning-upgrades.md`) and the reviewer's required changes (`docs/spec/reviews/plan-review.md`). `docs/spec/review-response.md` traces each one.
> - **Sources**: the old root PRD is superseded for execution. Build whitepaper v2 wins on scientific conflicts.

## Problem Statement

A kidney researcher looking at a spatial-transcriptomics atlas wants to know which reported cell states and disease differences deserve months of follow-up. Every one of them depends on how the instrument assigned RNA molecules to cells, and assignment errors can manufacture or hide a signal (Mitchel et al., Nature Genetics 2026).

Today the researcher either trusts the default assignment or writes one-off scripts. There is no workspace where they can:

- ask a question
- see whether the answer changes when the assignment rule changes
- check that change against what random molecule loss alone would produce
- confirm that the claims written about it match their numbers and figures
- hand a reproducible record to their PI

The judges need to see this working on real data within a few minutes, from a public URL that keeps working during judging (Nov 4–8), when model credits may already have lapsed. They also need to see why an agent is needed at all: its reasoning and its vision must do work a static dashboard cannot.

## Solution

SpatialScout is an assignment-sensitivity investigation workspace backed by an agent built on Meta's models.

**Ask and plan.** The researcher asks a question, typed or spoken: "Do the podocytes this atlas calls 'endocytic' really carry LRP2 and CUBN, or is that segmentation?" Muse Wonder reads the dataset's capability report and proposes a plan limited to supported tools. The researcher approves it.

**Audit.** Deterministic tools audit the four primary assignment conditions: default, nucleus-only, and distance caps of 1 and 2 µm.

**Choose the controls.** Muse Spark 1.3 reads each observation and decides which controls it needs, citing why:

- a random-thinning control, to test whether a drop exceeds what molecule loss explains
- a label-sensitivity check, to test whether the result depends on how the cells were labelled

Verification fails any claim that lacks a required control, so the agent's choices carry weight and are never cosmetic.

**Inspect the tissue.** The viewer flies to the top-ranked evidence region of a real GSE286184 section and shows:

- every molecule
- nuclei by cell type label
- excluded molecules in yellow
- a split slider between conditions
- retention and the thinning expectation beside every number
- SAM 3.1 glomerulus outlines, drawn on an image made from the RNA itself, as a layer badged exploratory

**Draft.** Claims are drafted in parallel by Muse Spark Open on Baseten.

**Verify.** Every claim is verified three ways:

- **Structurally**: references, counts and required controls.
- **Numerically**: an independent recompute of every cited number.
- **Visually**: Muse Spark 1.3 reads a two-panel figure. Panel A is a per-section chart. Panel B is the tissue crop. The model checks both against the claim.

**Challenge the verifier.** A judge can open "Challenge the verifier" on a claim card and swap in recorded injected errors, to see what the checks actually caught.

**Review and export.** The researcher records a review decision and exports an evidence package: claims, figures, a hash-linked audit log anchored by its head hash, a notebook, and replay instructions.

**Public URL.** It plays a labelled, immutable replay of a recorded live investigation. Live runs are gated.

**The hero question.** It is a descriptive audit of a published cell state, not a disease contrast. The GSE286184 authors reclassified podocytes co-expressing LRP2/CUBN as "Podocyte endocytosis". Disease contrasts (DKD, IgAN, MCD and MN vs Control) are descriptive in this release, because the 22 sections come from 19 donors with no published mapping (ADR-0007). The demo tells whatever story the frozen pipeline computes; no outcome is written in advance (ADR-0001).

## User Stories

### Asking and planning

1. As a researcher, I want to type a question about a gene, cell population and condition, so that I can start an investigation without code.
2. As a researcher, I want to hold a button and speak my question, so that I can ask hands-free.
3. As a researcher, I want to edit and confirm the transcript before it is used, so that a misheard gene never drives an analysis.
4. As a researcher, I want one-click example questions, so that I can see what this dataset supports.
5. As a researcher, I want the capability report shown before any plan, so that I know what is supported, unavailable and why.
6. As a researcher, I want every contrast's inference eligibility shown, so that I never read a descriptive comparison as an inferential one.
7. As a researcher, I want the planner limited to supported tools, so that I am never shown an analysis the data cannot back.
8. As a researcher, I want the plan to state the population, genes, conditions, tools and budget, so that I know exactly what will run.
9. As a researcher, I want to approve or reject the plan, and approving twice must never run it twice, so that nothing runs without my go-ahead.
10. As a researcher, I want an approved plan frozen, with any contrast-changing follow-up recorded as an exploratory branch, so that adaptive analysis is never mistaken for the pre-specified one.
11. As a researcher, I want the investigation to stop at its 12-call budget and return what it has plus open questions, so that the agent cannot fish for a favourable result.

### Watching the agent reason

12. As a researcher, I want to see each tool observation the agent receives, so that I can follow its reasoning.
13. As a researcher, I want to see which control the agent chose next and the observation it cited, so that I can judge whether its scientific reflexes are sound.
14. As a researcher, I want the agent to test a drop in co-expression against a random-thinning expectation, so that molecule loss is not mistaken for admixture.
15. As a researcher, I want the agent to check whether a result depends on the cell type label rule, so that a population selected on the genes it measures is caught.
16. As a researcher, I want a claim that skipped a required control to fail verification, so that the agent is accountable for its choices.

### Seeing the tissue

17. As a researcher, I want a real section with every molecule coloured by gene and nuclei by cell type label, so that I can inspect raw evidence.
18. As a researcher, I want to compare default with a stricter condition through a split slider, so that I can see exactly what changes.
19. As a researcher, I want excluded molecules highlighted in yellow, so that I can see which molecules a condition drops.
20. As a researcher, I want retention and the thinning expectation beside every audit number, so that dropping molecules never looks like a free improvement.
21. As a researcher, I want clicking a finding to fly the viewer into its top-ranked evidence region with the gene filter locked, so that every number links to tissue in one click.
22. As a researcher, I want the ranking rule shown and the ability to step to ranks 2 and 3, so that the first region does not read as cherry-picked.
23. As a researcher, I want glomerulus outlines from SAM 3.1 shown as an exploratory layer, so that I can orient myself without mistaking them for validated anatomy.
24. As a researcher, I want each outline compared with its seed box and a geometric baseline, with coverage and retention beside tuft-gene consistency, so that I can judge what SAM adds.
25. As a researcher, I want approximate cell outlines labelled as approximations, so that I do not mistake them for measured boundaries.
26. As a researcher, I want pan and zoom to stay smooth on a whole section, so that inspection feels immediate.

### Assignment audit

27. As a researcher, I want molecules counted under default, nucleus-only and distance-cap conditions, so that I can see how sensitive a result is to assignment.
28. As a researcher, I want populations fixed under the default condition, so that a cell losing all its molecules does not vanish from the denominator.
29. As a researcher, I want a co-expression score over exclusive marker pairs frozen from a single-nucleus reference, so that the admixture proxy was not tuned on the data it scores.
30. As a researcher, I want both a cell-matched and a home-matched thinning expectation, so that a gene whose mRNA is naturally cytoplasmic is not mistaken for admixture.
31. As a researcher, I want the share of excluded molecules lying closer to a neighbouring home-type cell than to their own cell, beside the same share for retained molecules, so that the spatial pattern behind an exclusion is measured, not eyeballed.
32. As a researcher, I want the hero result reported under both the full-panel and the NPHS1-anchored label rules, so that I can see whether the population's definition drives it.
33. As a researcher, I want a condition that cannot be computed reported as unavailable, so that a missing input never counts as evidence.

### Disease contrasts

34. As a researcher, I want per-section values and effects for each disease vs Control under every primary condition, so that I can see the whole picture.
35. As a researcher, I want contrasts labelled by the same frozen rules as audits, so that labels are consistent and explainable.
36. As a researcher, I want no p-values or confidence intervals that assume independent sections, so that pseudo-replication is never presented as evidence.
37. As a researcher, I want the 22-sections-from-19-donors limitation disclosed wherever sections are counted, so that I do not over-read replication.

### Claims and verification

38. As a researcher, I want each claim written as a sentence that cites its numbers in cautious wording, so that I can read results without over-reading them.
39. As a researcher, I want claims drafted in parallel, so that many results are covered quickly.
40. As a researcher, I want separate evidence, verification and review statuses on every claim, so that a numerically correct claim is not mistaken for an approved one.
41. As a researcher, I want every cited number recomputed by an independent code path, so that a model cannot invent a number.
42. As a researcher, I want the vision model to check the claim against both a statistical chart and the tissue crop, so that a sentence cannot contradict its evidence in either form.
43. As a researcher, I want a figure disagreement to mark the claim disputed and open it for review, so that I decide, not the model.
44. As a researcher, I want numerical or structural failures blocked from the validated summary but kept in history, and corrections to create new versions, so that errors are visible but contained.
45. As a judge, I want to inject any recorded error kind into a claim and see the verifier's recorded outcome, including misses, so that I can probe verification myself.
46. As a researcher, I want measured detection and false-rejection rates on a benchmark of valid and injected claims, so that I know how far to trust verification.

### Review, audit and export

47. As a PI, I want to accept, ask for more investigation or leave unresolved, by click or confirmed voice, so that the final decision is mine and recorded.
48. As a PI, I want every tool call, model call and decision in an append-only, hash-linked audit log whose head hash is exported, so that edits relative to that anchor are detectable.
49. As a PI, I want the run mode of every model response recorded, so that I know what was computed live, rerun with stored responses, or replayed.
50. As a PI, I want an evidence package with claims, figures, audit log and a notebook that re-runs the numerical checks, so that reproduction does not depend on SpatialScout running.
51. As a PI, I want separate instructions for a full rerun from raw GEO data, so that replay and computational reproducibility are not conflated.
52. As a PI, I want work-in-progress exports to show their review state, so that an unreviewed package is never mistaken for a final one.

### Judges, operators and developers

53. As a judge, I want the public URL to play a complete investigation without failing, labelled as an immutable replay with its recording time, so that I can evaluate it during judging.
54. As a judge, I want telemetry showing which Meta model and provider handled each step, so that I can see the Meta tooling at work.
55. As a judge, I want the golden path to finish in under three minutes, so that it fits a short video.
56. As a judge, I want a README separating implemented features from the roadmap, with only measured numbers, so that I can trust what I read.
57. As an operator, I want live runs behind a passcode and a file-locked daily budget, so that a public URL cannot overspend even with parallel calls.
58. As an operator, I want model calls cached by a key that includes tool version and artifact checksum, so that a stale response never serves changed inputs.
59. As an operator, I want investigations persisted with ordered events and reconnection from the last event, so that a refresh or Modal's 150-second request limit never loses work.
60. As an operator, I want failover from Baseten to Fireworks for open-weights calls, so that one outage does not break drafting.
61. As an operator, I want the batch audit across all 22 sections runnable as one command, locally or on Modal, so that tables regenerate from code.
62. As a developer, I want one source of truth for contracts with generated TypeScript types, so that backend and frontend cannot drift.

## Implementation Decisions

### Modules (deep modules: one Python package plus one web app)

- **Dataset store.**
  - Loads GSE286184 sections into validated molecule and cell tables, filtered to `qv ≥ 20` and panel genes. Unmatched records are counted, never dropped silently.
  - Writes the dataset manifest and the capability report. The report includes each contrast's inference eligibility.
  - Freezes two cell type label rules (see Frozen rules).
- **Analysis engine.** All deterministic science sits behind tool operations:
  - compute assignment conditions per molecule
  - audit a population: retention, nuclear overlap, observed value, both thinning expectations, excess drop, neighbour-proximity share, evidence regions
  - run the random-thinning control
  - run the label-sensitivity check
  - compute a descriptive disease contrast
  - label results by the frozen rules
  - build a region view
  - render a composite figure
  - recompute any claim's cited numbers by an independent path
- **Structure finder (exploratory).** Builds SAM 3.1 glomerulus outlines from box prompts on a gene-agnostic nucleus image, seeded from merged NPHS1 clusters.
  - Compares each outline with its seed box and a convex-hull baseline.
  - Allows empty, fragmented or rejected proposals.
  - Versions every mask (ADR-0005, narrowed by ADR-0006).
- **Model gateway.** One client for Meta (Wonder, Spark 1.3, SAM 3.1, Voice Transcribe), Baseten and Fireworks (Muse Spark Open). It provides:
  - a content-addressed cache
  - run-mode sources
  - local Pydantic validation with one bounded repair
  - a passcode and a file-locked budget reservation for live runs
  - failover
  - per-call telemetry
- **Investigation orchestrator.** A bounded state machine that persists `state.json` and `events.jsonl` (with a monotonic `seq`) per investigation and runs independently of any HTTP connection. The steps:
  1. question
  2. capability report
  3. plan (Wonder, schema-constrained, checked against the registry and capability report; one re-plan)
  4. idempotent approval
  5. tool execution
  6. agent-chosen follow-ups (Spark 1.3, 12-call budget, each citing an observation)
  7. parallel claim drafting (Spark Open)
  8. verification
  9. review
  10. export
- **Verifier.** Runs structural, numerical and visual checks:
  - Structural checks include required controls.
  - The numerical check is an independent recompute of every cited number.
  - The visual check is Spark 1.3 reading both figure panels.

  It also hosts the error injector and the benchmark runner.
- **Audit log.** Append-only and hash-linked, with a chain check. The head hash is exported in the package manifest; the golden path's head hash is also committed to the repo. Integrity is described as detecting edits relative to that anchor.
- **Evidence package exporter.** Writes claims, findings, composite figures, the audit log with its head hash, the run mode, a replay manifest, raw-rerun instructions, and a notebook that re-runs the numerical verification.
- **HTTP API.** FastAPI. Endpoints:
  - start an investigation
  - approve (idempotent)
  - stream events with `after_seq`
  - fetch a region view
  - transcribe WAV
  - record a review decision
  - export
  - list and play investigations

  It also serves the built web app (ADR-0004).
- **Web app.** React, TypeScript, Vite, Tailwind, deck.gl. Components:
  - question bar with push-to-talk
  - capability report
  - plan stepper with approve
  - agent reasoning timeline: observation → chosen control → result
  - telemetry pills
  - split viewer with fly-to-evidence and rank stepping
  - exploratory SAM layer
  - findings table
  - claim cards with the verification panel and "Challenge the verifier"
  - review controls
  - audit ticker
  - export
  - run-mode banner

### Contracts

Pydantic models are the single source of truth; JSON Schema and TypeScript types are generated from them. Every artifact has a schema version and an immutable id.

**Finding** is a discriminated union on `finding_kind`:

- **`audit`: an audit result.**
  - **Population:** label rule id, cell type and fixed counts.
  - **Genes or gene pair.**
  - **Per section and condition:**
    - observed value and retention
    - nuclear-overlap share
    - cell-matched and home-matched thinning expectations, with the excess drop against each
    - cells with at least one retained molecule
    - neighbour-proximity share for excluded and for retained molecules
  - **Evidence regions,** with the ranking rule.
  - **Label,** plus the exploratory condition's values kept apart.
- **`contrast`: a contrast result.**
  - **Disease and control groups.**
  - **Per section and condition:** library-size-normalised log2 values.
  - **Per condition:** effect.
  - **Leave-one-section-out influence.**
  - **`inference_eligibility`:** `descriptive_only` plus its reason.
  - **Label,** plus the exploratory condition's values kept apart.

Claim shape:

```json
{
  "schema_version": "2.0",
  "claim_id": "clm-…", "version": 1, "investigation_id": "inv-…", "dataset_id": "GSE286184",
  "finding": {"finding_id": "fnd-…", "finding_kind": "audit | contrast"},
  "text": "…",
  "cited": {"…": "every number the text uses, with its source field"},
  "controls": {"random_thinning": "ctl-… | null", "label_sensitivity": "ctl-… | null"},
  "figure_id": "fig-…",
  "evidence_status": "stable | segmentation_sensitive | insufficient_evidence",
  "verification_status": "pending | verified | failed | disputed | unavailable",
  "review_status": "unreviewed | accepted_for_follow_up | needs_investigation | unresolved",
  "injected": {"is_injected": false, "kind": null}
}
```

Investigation state: `state.json` holds status, `run_mode`, approved-plan hash and timestamps. `events.jsonl` holds one event per line, with a monotonic `seq` and its original `recorded_at_utc`. Missing values stay null with a reason.

### Frozen analysis rules

Write once, frozen before the primary run, and record them in every result. They supersede the spike's exploratory thresholds.

- **Label rules.**
  - The *full-panel rule* is the spike's one-or-two-markers-per-compartment argmax rule, applied to default counts with gene scales pooled from control sections.
  - The *NPHS1-anchored podocyte rule* decides podocyte membership without LRP2 or CUBN. It is the primary rule for the hero population.

  Both are reported for hero results (the label-sensitivity check). Neither is free of selection bias: the anchored rule can admit proximal-tubule cells carrying stray NPHS1. The panel contains no NPHS2, PODXL or WT1.
- **Conditions.**
  - *Primary* conditions are default, nucleus-only, and distance caps of 1 and 2 µm (non-nuclear molecules within the cap are kept).
  - The *exploratory* condition is structure-constrained, built from SAM 3.1 outlines. It is reported beside the primary conditions and never enters a label (ADR-0006).
- **Fixed populations.** Cells are labelled once under the default condition, and every condition is computed over the same cells. A cell with no retained molecules is non-expressing and stays in the denominator.
- **Gate precedence.** A section passes the *population gate* with at least 20 cells of the population, and the *molecule gate* with at least 10 of the result's molecules in that population. The gates apply in this order.
  - **Contrast results**, where every section is a replicate:
    1. Every section of both groups must pass the population gate. If any fails, the result is insufficient evidence.
    2. A condition is valid only if every section passes the molecule gate under it.
    3. The default condition plus at least one stricter primary condition must be valid. If not, the result is insufficient evidence.
  - **Audit results**, which ask how one population behaves, not how groups differ:
    1. A section is eligible when it passes the population gate and the molecule gate under the default condition.
    2. At least 3 sections must be eligible. If fewer are, the result is insufficient evidence.
    3. Every condition is computed over the same eligible sections, drawn from all 22 sections with a breakdown by group. The eligible sections are listed in the result.

    Stricter conditions are not molecule-gated, because what they retain is the measurement and the thinning expectation already accounts for low counts.
- **Near-zero band.** A value within ±0.1 (log2 units) has no direction. A reversal needs two valid conditions with opposite non-zero directions.
- **Contrast labels.**
  - **Stable:** at least two valid primary conditions, no reversal, and an effect range of at most 0.5 log2. Leaving out any one section must never produce an opposite non-zero direction in any valid condition.
  - **Segmentation-sensitive:** a reversal or a range above 0.5, with the default effect stable under leave-one-section-out.
  - **Insufficient evidence:** anything else.
- **Audit labels.** Use the home-matched expectation *E* and the observed value *O*, pooled over the eligible sections, under each stricter primary condition.
  - **Segmentation-sensitive:** in at least one such condition, *O* < *E* × 2^−0.5 (an excess log2 drop above 0.5), and this holds when any one eligible section is left out.
  - **Stable:** every such condition has *O* ≥ *E* × 2^−0.5, and this holds when any one eligible section is left out.
  - **Insufficient evidence:** anything else, including fewer than 3 eligible sections or a gene with no home cell type.
- **Thinning expectations (closed form).** For cell *c* with *k* default molecules of gene *g*:
  - **Retention probabilities:**
    - *cell-matched:* p = 1 − (1 − r_c)^k, where r_c is the cell's retention
    - *home-matched:* p = 1 − (1 − ρ_{g,κ})^k, where ρ_{g,κ} is gene *g*'s retention in its home cell type under condition κ, in that section
  - **Expected values:**
    - share expressing: the mean of *p* over the fixed population
    - gene set (for example LRP2 or CUBN): 1 − Π(1 − p_g)
    - pair co-expression: Σ p_g·p_h / Σ(p_g + p_h − p_g·p_h)
  - **Excess drop:** expectation minus observed.
- **Contrast effects.**
  - **Normalisation:** library size, as the pseudobulk total of the population in that section and condition.
  - **Value:** log2(CP10K + 1).
  - **Effect:** the difference between group means.

  There are no p-values or confidence intervals in this release (ADR-0007). Inferential tests and their multiple-testing family move to the roadmap, pending donor metadata.
- **Exclusive marker pairs** come from the frozen artifact `configs/exclusive_marker_pairs.json`, built from GSE271188 control donors before any Xenium evaluation.

### Verification scope

**Structural checks:**

- schema validity
- the dataset and finding references resolve
- section counts match
- required controls are present:
  - a home-matched thinning control for any claim about assignment sensitivity
  - a label-sensitivity check for any claim about a population whose label rule involves the claim's genes, or decides membership against those genes' home cell type (the NPHS1-anchored podocyte rule competes with proximal tubule, the home type of LRP2/CUBN)

**Numerical check.** An independent code path recomputes every cited number from the stored molecule tables, within declared tolerances:

- population counts
- per-section molecule sums
- retention
- observed values
- both expectations
- neighbour-proximity shares
- contrast effects
- direction

No fitted model is involved, so every cited number is reproducible.

**Visual check.** Muse Spark 1.3 reads the composite figure and returns, against a schema:

- whether Panel A's direction matches the claim
- whether a single section drives Panel A
- whether Panel B shows the neighbour pattern the claim states

The Panel B answer is backed by the computed neighbour-proximity shares, so the question is never one the image answers by construction. A visual check is a consistency check, not ground truth.

**Outcomes.**

- A failed structural or numerical check blocks the claim from the validated summary.
- A visual disagreement marks it disputed.
- An unavailable check stays unavailable.
- A correction creates a new version.

**Error injector kinds:** reversed direction, wrong section count, wrong dataset reference, changed effect, figure-label mismatch, misstated spatial pattern, missing required control.

### Run modes

- **`immutable_replay`** streams a recorded `events.jsonl` verbatim, with its original timestamps.
- **`cached_tool_rerun`** re-executes the deterministic tools on current artifacts and serves stored model responses. The cache key is a hash of provider, model, inputs, response schema version, tool version and artifact checksum.
- **`live`** makes fresh model calls under the passcode and a file-locked daily budget reservation.

The banner and the audit log always state the mode (ADR-0003).

### Model jobs (every model does real work)

| Model / platform | Job |
| --- | --- |
| Muse Wonder (`muse-wonder-1.0`) | Schema-constrained plan limited to the capability report |
| Muse Spark 1.3 (`muse-spark-1.3`) | Reads observations and chooses follow-up controls with cited reasons; explains; verifies both figure panels by vision |
| SAM 3.1 (`sam-3.1`) | Exploratory glomerulus outlines from box prompts on RNA-derived images |
| Muse Voice Transcribe (`muse-voice-transcribe-1.0`) | Push-to-talk questions and confirmed review decisions |
| Muse Spark Open on Baseten (`meta-models/muse-spark-open`) | Parallel claim drafting |
| Muse Spark Open on Fireworks (`accounts/fireworks/models/muse-spark-open`) | Failover for open-weights calls |
| Modal | Hosting with Volume-backed investigation state; batch audit with `.map()` |

### Specific interactions

- **Claim wording.** Claims use cautious, population-scoped wording, for example: "Co-expression persists under the tested restriction in cells labelled by our marker rule." They never imply replication of the authors' labels or proof of a biological state.
- **Voice.** The browser records PCM and encodes 16-bit mono WAV at 16 kHz itself. The transcript is editable and must be confirmed.
- **Region view.** It ships molecules as compact columns: positions, gene index, cell index and per-condition inclusion bits. A whole section of about 300k molecules renders at once. Fly-to-evidence animates over about 800 ms.
- **Long investigations.** Each SSE connection closes before Modal's 150-second limit, and the client reconnects with `after_seq`.

## Testing Decisions

- **What makes a good test:** it checks behaviour through a public interface, against an expected value from an independent source (a hand-built example or a worked calculation). It never re-runs the implementation's own logic.
- **Seam 1: the analysis engine's public operations,** on tiny hand-built tables with answers known by construction:
  - expansion-zone exclusion
  - retention and the co-expression score
  - fixed-population denominators
  - both thinning expectations against worked examples, cross-checked by a seeded Monte Carlo simulation
  - the neighbour-proximity share
  - evidence-region ranking
  - both label rules, including a cell whose label differs between them
  - every gate-precedence and label case, including near-zero effects
  - the independent recompute agreeing with the engine and catching every deterministic error kind
  - SAM mask placement, on a recorded response
  - the exploratory condition never changing a label
- **Seam 2: the HTTP/SSE API,** through FastAPI's test client with recorded model responses:
  - the question-to-package event sequence
  - refresh at approval, duplicate approval and reconnect with `after_seq`
  - agent-chosen controls in the hero run
  - a skipped control ending in a structural failure
  - an injected error ending failed or disputed
  - budget and passcode refusal, including concurrent reservations
  - export contents and the chain check
- **No UI unit tests.** One Playwright smoke run of the immutable replay against the deployed URL, at the end.
- **Model quality** is measured by the verification benchmark (at least 20 valid and 20 injected claims, with a held-out subset), not by unit tests.
- **Prior art:** `spikes/` holds reference computations whose worked examples seam-1 tests may borrow. The spikes' labels themselves are not imported.

## Out of Scope

- Inferential statistics (p-values, confidence intervals, multiple-testing control) and PyDESeq2 fits for disease contrasts, pending verified donor metadata (ADR-0007).
- Anatomical accuracy claims for SAM outlines; SAM 3.1 fine-tuning; tile-video stitching.
- Re-segmentation or correction tools (Proseg, Cellpose-SAM, cellAdmix, 2DE).
- Datasets other than GSE286184 and its single-nucleus reference; lupus-nephritis framing.
- A urine-biomarker bridge beyond, at most, one VCAM1 card labelled as a candidate tissue association.
- Live Muse Glimmer LoRA serving; the offline agreement study is a stretch goal after ticket 12.
- Arbitrary code execution by the agent; accounts; clinical use (outputs are research hypotheses only).

## Further Notes

### Demo storyboard (about 2.5 minutes, written from computed outputs)

1. **Hook.** A 2026 kidney atlas reports "Podocyte endocytosis". Is it biology, or where the instrument drew the cell edges?
2. **Ask and plan.** The researcher asks, by voice if ticket 08 has landed. Muse Wonder proposes a plan limited to what the capability report supports, and the researcher approves it.
3. **The agent reasons.** The audit returns. Muse Spark 1.3 notes the retention drop and chooses the random-thinning control and the label-sensitivity check, citing what it saw. Their results appear in the reasoning timeline.
4. **The tissue.** The viewer flies into the top-ranked evidence region, with the ranking rule shown. The split slider moves from default to nucleus-only; excluded molecules light yellow, with the expectation beside the observed value. SAM 3.1 outlines appear as an exploratory layer.
5. **Draft and verify.** Claims are drafted in parallel on Baseten. Muse Spark 1.3 checks the chart and the tissue crop. A judge opens "Challenge the verifier" and sees the recorded outcome of an injected error.
6. **Review and export.** A review decision is recorded, the package is exported, and the head hash is shown. Telemetry shows every Meta model and partner used.

### Schedule and human-only steps

- **Nov 2:** walking skeleton with persisted investigations; real data and label rules; marker pairs frozen.
- **Nov 3:** audit with controls, the agent loop on audit results, verification, review and export, then contrasts and the enhancements. Record the golden path live.
- **Nov 4:**
  - Polish in the morning, and record the demo video late morning (this needs you).
  - Freeze code at about 1 PM CT and make the repo public.
  - Submit by about 5 PM CT.
  - Push nothing after 8 PM CT: a repository change after the deadline marks the project late.
- **Muse Code** was not used, and the submission must not claim it.

### Risks

| Risk | Mitigation |
| --- | --- |
| Credits lapse during judging | Immutable replay by default (ADR-0003) |
| Sparse podocyte counts | Gate precedence and insufficient-evidence labels |
| Unknown donor mapping | Descriptive contrasts (ADR-0007) |
| Imperfect SAM outlines | Exploratory, compared with baselines, never labelled (ADR-0006) |
| Location-dependent molecule loss | The home-matched thinning expectation |
