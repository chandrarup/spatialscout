# SpatialScout

SpatialScout investigates which spatial-transcriptomics results in kidney tissue still hold when the rule for assigning RNA molecules to cells changes. It turns a researcher's question into a checked, reviewable evidence package.

## Tissue data

**Section**:
One tissue section measured on the Xenium instrument; one GEO sample.
_Avoid_: sample, slide, biopsy, specimen

**Donor**:
The person a section came from. Several sections can share a donor.
_Avoid_: patient, subject

**Panel**:
The fixed set of genes the assay measured (50 genes in GSE286184).
_Avoid_: gene list, features

**Molecule**:
One decoded RNA molecule with a gene, a position in micrometres and a quality score.
_Avoid_: transcript, read, spot, dot

**Cell**:
A cell found by the instrument's own segmentation, with a centroid and a nucleus.
_Avoid_: segment, object

**Label rule**:
A frozen, named rule that assigns cell type labels from marker counts under the default condition.
_Avoid_: classifier, annotation method

**Cell type label**:
The cell type a label rule assigns to a cell, frozen for every assignment condition.
_Avoid_: cluster, annotation (as a noun for the label)

**Home cell type**:
The cell type a marker gene marks, used as the reference for how that gene's molecules sit inside cells.
_Avoid_: source cell, origin

**Structure**:
A multicellular anatomical unit of the tissue, such as a glomerulus.
_Avoid_: ROI, compartment

**Structure mask**:
The outline of one structure in section coordinates.
_Avoid_: segmentation, polygon (as the domain term)

**Region**:
A rectangular window of a section that the viewer shows and a claim can point to.
_Avoid_: ROI, tile, field of view

**Evidence region**:
A region ranked by a stated rule as showing the molecules behind a finding.
_Avoid_: hotspot, best region

## Assignment audit

**Assignment**:
The mapping of molecules to cells.
_Avoid_: segmentation (SpatialScout does not re-segment)

**Assignment condition**:
A rule that decides which molecules count toward a cell.
_Avoid_: segmentation method, pipeline, correction

**Primary condition**:
An assignment condition that evidence labels are computed over: default, nucleus-only, or a distance cap.
_Avoid_: main condition

**Exploratory condition**:
An assignment condition reported beside the primary conditions but never used in an evidence label; here, the structure-constrained condition.
_Avoid_: experimental condition, beta

**Default condition**:
The instrument's own molecule-to-cell assignment, used unchanged.
_Avoid_: 10x default segmentation, baseline

**Excluded molecule**:
A molecule counted toward a cell under the default condition but not under the condition being compared.
_Avoid_: leaked molecule, contaminant

**Retention**:
The share of default-condition molecules that a condition keeps.
_Avoid_: signal retained, recovery

**Admixture**:
Molecules from one cell counted toward a neighbouring cell.
_Avoid_: contamination, leakage, bleed

**Co-expression score**:
For a set of exclusive marker pairs, the average share of cells expressing either marker that express both; a proxy for admixture, not a calibrated rate.
_Avoid_: contamination rate, purity

**Exclusive marker pair**:
Two genes that mark different cell types and rarely occur in the same nucleus of the frozen single-nucleus reference.
_Avoid_: mutually exclusive markers

**Random-thinning expectation**:
The value a measure would take if a condition removed molecules at random at a matched rate: the cell's own retention (cell-matched) or the gene's retention in its home cell type (home-matched).
_Avoid_: null model, permutation baseline

**Excess drop**:
A random-thinning expectation minus the observed value; large when a condition removes more of a signal than random molecule loss explains.
_Avoid_: artifact score, leakage score

**Neighbour-proximity share**:
The share of a gene's molecules that lie closer to a cell of the gene's home type than to their own cell's centroid.
_Avoid_: boundary score

## Findings and evidence

**Finding**:
A computed result a claim can cite: an audit result or a contrast result.
_Avoid_: hit, signal, target, DE gene

**Audit result**:
How a measure of one cell population (a gene's presence, a gene set's presence or a co-expression score) behaves across assignment conditions, per section, with its random-thinning expectations.
_Avoid_: descriptive finding, QC metric

**Contrast**:
The comparison of one disease group with the control group, for example DKD vs Control.
_Avoid_: comparison, test

**Contrast result**:
The disease-vs-control effect for one gene in one cell type under every assignment condition, with per-section values.
_Avoid_: differential expression, DE result

**Effect**:
A contrast result's log2 ratio of group means under one assignment condition.
_Avoid_: score, delta

**Inference eligibility**:
Whether a contrast's groups support statistical inference; in this release every contrast is descriptive only.
_Avoid_: significance, power

**Evidence label**:
What the evidence supports about a finding: stable, segmentation-sensitive or insufficient evidence. It says nothing about biological truth.
_Avoid_: robust, artifact, newly revealed, significant

**Stable**:
The finding holds across every valid primary condition by the frozen rules, including when any one section is left out.
_Avoid_: robust, validated, real

**Segmentation-sensitive**:
The finding reverses, moves beyond the frozen range, or drops beyond its random-thinning expectation between valid primary conditions.
_Avoid_: artifact, false positive, fake

**Insufficient evidence**:
Too few cells, molecules, sections or valid primary conditions to label the finding.
_Avoid_: not significant, failed

**Label-sensitivity check**:
The comparison of a finding under two label rules, one of which does not use the finding's own genes.
_Avoid_: robustness check, ablation

**Required control**:
A check a claim must cite before it can be verified: a random-thinning control for claims about assignment sensitivity, and a label-sensitivity check for claims about a population whose label rule involves the claim's genes or decides membership against those genes' home cell type.
_Avoid_: optional check, sanity check

## Investigation

**Question**:
What the researcher asks SpatialScout, typed or spoken.
_Avoid_: query, prompt

**Capability report**:
For a dataset, which analyses are supported, unavailable or descriptive only, each with its reason.
_Avoid_: data check, validation report

**Transcript**:
The editable text of a spoken question, which the researcher confirms before anything runs. Never used for RNA molecules.
_Avoid_: caption, dictation

**Plan**:
The ordered tool steps proposed for a question, limited to what the capability report supports; frozen once approved.
_Avoid_: DAG, workflow, pipeline

**Investigation**:
One persisted run from a question through plan, tool calls, claims and verification to an evidence package.
_Avoid_: session, job, analysis run

**Tool**:
A deterministic analysis operation the agent may call from a fixed registry.
_Avoid_: function, skill, MCP tool (as the domain term)

**Observation**:
A tool's result as the agent receives it, which a follow-up request must cite.
_Avoid_: output, response

**Claim**:
A sentence about a finding plus the numbers, controls and figure it cites, carrying separate evidence, verification and review statuses.
_Avoid_: hypothesis, statement, result

**Composite figure**:
A claim's two-panel figure: per-section values across conditions, and a tissue crop of its top evidence region.
_Avoid_: plot, chart (for the whole figure)

**Verification**:
The structural, numerical and visual checks run on a claim.
_Avoid_: validation, fact-check

**Sub-claim**:
One testable part of a question: a cell type, its genes, and whether the researcher's hypothesis predicts the signal holds or drops under stricter assignment. A prediction, never an outcome.
_Avoid_: hypothesis (for the part), expectation

**Verdict**:
Confirmed, refuted or inconclusive for one sub-claim, derived by a frozen rule from its verified claims' evidence labels. Like an evidence label, it is scoped to the sections, regions and controls behind it and says nothing about biological truth.
_Avoid_: proof, validated, artifact, true positive

**Disputed**:
A claim whose visual check disagrees with its figure; it stays visible and flagged for review.
_Avoid_: rejected, false

**Injected error**:
A deliberately altered claim used to test verification, always labelled as injected.
_Avoid_: planted claim, fake claim, lie

**Review decision**:
The researcher's decision on a claim: accept for follow-up, request more investigation, or leave unresolved.
_Avoid_: sign-off, approval

**Plan approval**:
The researcher's go-ahead that freezes a plan; approving again changes nothing.
_Avoid_: sign-off

**Audit log**:
The append-only, hash-linked record of every tool call, model call and decision in an investigation. Edits are detectable relative to an exported head hash, not prevented.
_Avoid_: audit trail, provenance chain, tamper-proof log

**Evidence package**:
The export of an investigation: claims, figures, audit log with its head hash, and the instructions to replay or rerun it.
_Avoid_: report, bundle, notebook (the notebook is one part)

**Run mode**:
How an investigation's events were produced: immutable replay, cached tool rerun or live run. Always shown.
_Avoid_: demo mode, offline mode

**Immutable replay**:
Playback of a recorded investigation's events verbatim, with their original timestamps.
_Avoid_: replay mode, cached mode

**Cached tool rerun**:
Re-execution of the deterministic tools on current artifacts, with stored model responses.
_Avoid_: warm run, re-execution

**Live run**:
An investigation that makes fresh model calls under the spend budget.
_Avoid_: live mode, real mode, online mode

## The lab

**Lab**:
The follow-up phase on a finished investigation: sub-agents dispatched by Muse Wonder, run at the same time, and a report assembled in code. It never changes the verdict.
_Avoid_: post-processing, extras

**Sub-agent**:
One lab task from the fixed registry: a literature review, a protein cross-check or a publication figure, about one sub-claim.
_Avoid_: worker, swarm agent

**Literature review**:
A sub-agent's reading of the records Europe PMC returned for one query: cited statements only, plus a count of the records that pair the gene with the cell type in human tissue.
_Avoid_: novelty check, prior-art search

**Uploaded section**:
A researcher's own Xenium section (a transcripts file and a cells file), audited for one request and not kept.
_Avoid_: user sample, customer data

## The data check

- **Data check**: before a question that no recording answers runs, the reading in code of what it needs (genes,
  cell types, disease groups, organ, species, assay) against what the workspace holds ([ADR-0009](docs/adr/0009-the-data-check.md)).
- **Hard gap**: a need no run here can meet (a gene off the panel, an unlabelled cell type, another organ, species or
  assay); the question does not run. **Soft gap**: a need a run would answer only nearby (a disease the cohort lacks).
- **Public dataset**: a GEO record the data check's live search returned for the question's needs; "audit it here"
  only when it is human Xenium output.

