# SpatialScout

SpatialScout investigates which spatial-transcriptomics findings in kidney tissue still hold when the rule for assigning RNA molecules to cells changes. It turns a researcher's question into a checked, reviewable evidence package.

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

**Cell type label**:
SpatialScout's marker-based label for a cell, assigned once and frozen for every assignment condition.
_Avoid_: cluster, annotation (as a noun for the label)

**Structure**:
A multicellular anatomical unit of the tissue, such as a glomerulus.
_Avoid_: ROI, compartment

**Structure mask**:
The outline of one structure in section coordinates.
_Avoid_: segmentation, polygon (as the domain term)

**Region**:
A rectangular window of a section that the viewer shows and a claim can point to.
_Avoid_: ROI, tile, field of view

## Assignment audit

**Assignment**:
The mapping of molecules to cells.
_Avoid_: segmentation (SpatialScout does not re-segment)

**Assignment condition**:
A rule that decides which molecules count toward a cell: default, nucleus-only, distance cap, or structure-constrained.
_Avoid_: segmentation method, pipeline, correction

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
Two genes that mark different cell types and rarely occur in the same nucleus in a reference.
_Avoid_: mutually exclusive markers

## Findings and evidence

**Contrast**:
The comparison of one disease group with the control group, for example DKD vs Control.
_Avoid_: comparison, test

**Finding**:
The disease-vs-control effect for one gene in one cell type, estimated under every assignment condition.
_Avoid_: hit, signal, target, DE gene

**Effect**:
A finding's log2 fold change under one assignment condition.
_Avoid_: score, delta

**Evidence label**:
What the evidence supports about a finding: stable, segmentation-sensitive or insufficient evidence. It says nothing about biological truth.
_Avoid_: robust, artifact, newly revealed, significant

**Stable**:
The effect keeps its direction and stays within the frozen range across every valid condition, and survives leaving out any one section.
_Avoid_: robust, validated, real

**Segmentation-sensitive**:
The effect reverses or moves beyond the frozen range between valid conditions.
_Avoid_: artifact, false positive, fake

**Insufficient evidence**:
Too few molecules, cells, sections or valid conditions to label the finding.
_Avoid_: not significant, failed

## Investigation

**Question**:
What the researcher asks SpatialScout, typed or spoken.
_Avoid_: query, prompt

**Capability report**:
For a dataset, which analyses are supported, failed or unavailable, each with its reason.
_Avoid_: data check, validation report

**Plan**:
The ordered tool steps proposed for a question, limited to what the capability report supports; frozen once approved.
_Avoid_: DAG, workflow, pipeline

**Investigation**:
One run from a question through plan, tool calls, claims and verification to an evidence package.
_Avoid_: session, job, analysis run

**Tool**:
A deterministic analysis operation the agent may call from a fixed registry.
_Avoid_: function, skill, MCP tool (as the domain term)

**Claim**:
A sentence about a finding plus the numbers and evidence it cites, carrying separate evidence, verification and review statuses.
_Avoid_: hypothesis, statement, result

**Verification**:
The structural, numerical and visual checks run on a claim.
_Avoid_: validation, fact-check

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
The researcher's go-ahead that freezes a plan.
_Avoid_: sign-off

**Audit log**:
The append-only, hash-linked record of every tool call, model call and decision in an investigation. Edits are detectable, not prevented.
_Avoid_: audit trail, provenance chain, tamper-proof log

**Evidence package**:
The export of an investigation: claims, figures, audit log and the instructions to replay or rerun it.
_Avoid_: report, bundle, notebook (the notebook is one part)

**Replay**:
Playback of a recorded investigation from stored model responses, always labelled as a replay.
_Avoid_: demo mode, offline mode, cached mode

**Live mode**:
An investigation that makes real model calls.
_Avoid_: online mode, real mode
