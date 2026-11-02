> Generated from `SpatialScout_Build_Whitepaper.docx` (Nov 2, 2026) with pandoc so agents can read it. The .docx is canonical.

**Product whitepaper and implementation blueprint**

Chandra rup · Version 2 · November 2, 2026

## Abstract

SpatialScout is a proposed research platform that helps scientists investigate which spatial biology findings remain supported when analytical assumptions change. Its first application is kidney disease research: inspect tissue, audit cell assignments, compare disease with control samples, and produce traceable hypotheses for expert review. The longer-term platform connects these findings to other omics, supports collaborative review, and makes analysis accessible through natural language and voice.

The central workflow begins with a scientist’s question and ends with an evidence package. Meta models plan investigations, invoke validated analysis tools, interpret tissue and plots, and explain the results. Deterministic software computes statistics and checks numerical claims. Scientists retain control of the analysis plan and final interpretation.

Development proceeds through complete, usable modules. The first release will support one dataset and one research task from ingestion to export. Additional modules add disease comparisons, structure-aware analysis, urine proteomics and model adaptation as time and evidence permit. Each release will distinguish implemented capabilities, measured outcomes and planned extensions. No performance gains or user-validation results are asserted in this design.

## The scientific problem

Spatial transcriptomics connects gene expression to locations in tissue. Incorrect assignment of molecules to cells can distort downstream interpretation. Mitchel and colleagues demonstrated substantial effects on differential expression and other analyses, and introduced cellAdmix to reduce molecular admixture \[1, 2\]. SpatialScout will build on such methods while making their assumptions, outputs and consequences inspectable.

The intended contribution is an integrated investigation workflow: identify a concern, examine the spatial evidence, compare analytical conditions, check claims, and record the researcher’s decision. A new segmentation algorithm is an optional research contribution, not a prerequisite for product value.

## The research decision we aim to improve

A researcher asks: “Which candidate signals deserve follow-up, and which require more scrutiny?” SpatialScout should make the evidence behind that decision easier to obtain and reproduce. Success may mean a faster investigation, detection of an erroneous claim, clearer uncertainty or improved analytical quality. It does not require discovering a new biomarker.

**Intended use:** exploratory research using public datasets. Outputs are research hypotheses, not diagnoses, treatment recommendations or patient-level predictions.

# 1 Researcher experience and release strategy

## A complete investigation

The researcher opens a validated dataset and asks a question, such as whether a measured gene differs between disease and control in a particular cell type. SpatialScout shows the available samples, gene coverage and analytical limitations before proposing a plan.

The researcher approves the contrast and methods. The agent runs the tools, exposes progress and opens an evidence view containing tissue or coordinate overlays, per-sample expression, method comparisons and a claim panel. If an apparent signal changes materially, the agent can inspect neighbouring cells, test sample influence or request a supported alternative analysis.

Every conclusion links to the data, parameters and computations that produced it. A researcher can accept a hypothesis for follow-up, request another investigation or leave it unresolved. Export produces the figures, machine-readable claims and instructions needed to reproduce the analysis.

## Modules that remain useful on their own

| **Module**                | **Completed user task**                    | **Release gate**                                          |
|---------------------------|--------------------------------------------|-----------------------------------------------------------|
| M0 Data foundation        | Know which analyses the dataset supports   | Validated manifest and capability report                  |
| M1 Inspect and audit      | Investigate questionable cell assignments  | Agent-led audit, linked evidence and export               |
| M2 Compare findings       | Assess sensitivity of a disease contrast   | Sample-level results across supported conditions          |
| M3 Verify and reproduce   | Check and replay a research claim          | Numerical checks, failure states and reproducible package |
| M4 Add biological context | Explore tissue structures and other omics  | Independent evidence for each additional inference        |
| M5 Adapt and expand       | Improve task performance and accessibility | Held-out evaluation or observed usability benefit         |

M3 is a progressively strengthened module: basic provenance and numerical checks begin in M1. They are not postponed until the end. M4 includes two separately gated capabilities: SAM-assisted structure inspection and tissue-to-urine exploration. SAM inspection can enter M1 when registered images are available.

## Minimum coherent submission

Deliver M0 and M1 with an integrated agent, evidence viewer and reproducible export. Add M2 when donor metadata and statistical inputs support it. The demonstration must work from a real question to an inspectable result; disconnected notebooks or unfinished screens do not satisfy the release gate.

The broader vision remains visible in a roadmap. Unimplemented features are labelled as planned, and a cached analysis is identified as a replay. An audit-only release can demonstrate inspection and verification without implying that disease-level inference has been completed.

# 2 Data readiness determines the first build

## Primary cohort and fallback

GSE286184 is the candidate glomerular-disease Xenium cohort \[3\]. Its GEO record lists 22 spatial samples. A sample protocol describes a targeted 50-gene panel \[4\]; therefore, the first ingestion task is to inventory actual feature coverage across all selected samples. Do not assume transcriptome-wide discovery or that every desired marker is measured. Verify disease labels, unique donors and the relation to the accompanying single-nucleus reference before defining a contrast.

The listed files include counts and transcript-related data, but the build must separately establish access to morphology images, cell boundaries and registration transforms. Missing images disable image-based functions; they do not automatically prevent a coordinate-based audit.

A fallback for visual integration is the public 10x human kidney preview dataset, which provides non-diseased and papillary renal cell carcinoma samples with associated imaging resources \[5\]. Use it to exercise ingestion, overlays and structure inspection. Its two-donor design does not support a replicated disease-versus-control claim. It also does not establish performance in lupus nephritis.

## Required capability checks

| **Capability**          | **Required inputs**                                 | **Behaviour if missing**                           |
|-------------------------|-----------------------------------------------------|----------------------------------------------------|
| Coordinate inspection   | Cell or transcript coordinates and units            | Disable spatial view                               |
| Assignment audit        | Counts, cell identifiers and method-specific inputs | Show exactly which checks remain supported         |
| Molecule reassignment   | Molecule locations and supported boundary inputs    | Do not infer assignments from a count matrix       |
| SAM structure view      | Tissue image and verified coordinate registration   | Disable overlays or use a separate image-only demo |
| Disease comparison      | Unique donors, groups and valid count inputs        | Restrict to descriptive results                    |
| Reference-based scoring | Compatible reference and measured marker coverage   | Mark score unavailable                             |

## Dataset manifest

Record dataset ID, source URL, source terms, download date, file checksums, assay, panel genes, sample-to-donor mapping, disease labels, stain, pixel size, coordinate units, transforms and reference provenance. A capability report records each check as passed, failed or unavailable with a reason.

Validate sparse-matrix dimensions, unique identifiers, nonnegative counts and joins between molecules, cells and metadata. Count unmatched records rather than silently dropping them. Overlay selected landmarks after registration and record the inspection. Multiple sections from one donor remain linked to that donor.

**First decision gate:** select the first dataset only after a small representative subset loads and the intended tool completes successfully. If a dependency fails within the initial investigation window, switch to the supported workflow and record the limitation.

# 3 Segmentation audit and structure analysis

## Separate three sources of change

A cell segmenter defines cell boundaries or assignments. A correction method adjusts suspected molecular admixture. A tissue-structure model locates larger anatomical regions. SpatialScout stores these as distinct operations. A glomerulus mask does not validate every cell boundary or prove the origin of every molecule.

Start with the supplied assignment and one compatible published correction method. cellAdmix is an R package, so its adapter will run in a version-pinned R environment with explicit input and output conversion \[2\]. Add alternative segmenters only after confirming their data requirements. A method failure is reported as unavailable; it never counts as evidence against a finding.

## Audit outputs

Report reference-based admixture indicators where supported, molecule retention, retained cells, cell-type composition and runtime for every condition. Keep raw data immutable. Store corrected outputs as separate versions with transformation provenance and their count semantics, such as integer counts or continuous estimates.

An optional marker-pair score measures unexpected co-expression among preselected pairs. For each pair, divide cells expressing both markers by cells expressing either; exclude zero-denominator pairs and report the number of eligible pairs. Report scores by sample and cell type with coverage and count-depth summaries. This is a proxy, not a calibrated contamination percentage. Sparse references, assay differences and real transitional cell states can also produce apparent disagreement.

Select marker pairs using a separate reference or a development split, freeze them before evaluation, and examine depth-matched sensitivity. Report marker-based scores alongside signal retention so deleting molecules cannot appear beneficial without its cost being visible. Keep annotation labels fixed for the primary comparison where possible; analyse reannotation separately.

## SAM as a testable contribution

Use SAM 3.1 to propose tissue structures on registered images, allowing a researcher to inspect or correct masks \[6\]. Save prompts, masks, coordinates and manual edits. Begin with structure localization and evidence navigation. A proposed constraint on transcript assignment should be a separately named experimental condition, not the default correction.

Evaluate localization using independent expert annotations. Evaluate any boundary constraint by comparing the same pipeline with and without it, including retained signal and downstream sensitivity. Marker enrichment can provide a biological consistency check, but markers used to create a mask must not serve as independent validation of that mask.

**Module acceptance:** a real region can be opened from an audit flag, the evidence behind the flag is visible, and the same inputs reproduce the stored metrics. Improvements are reported only after comparison with the baseline; a neutral or negative result is retained.

# 4 Disease comparisons and evidence labels

## Analysis unit and statistical contract

Choose one within-study disease contrast after inspecting donor counts and covariates. Aggregate counts by donor and cell type; if several sections belong to one donor, combine them using a documented rule or use an appropriate repeated-measures design. Cells, tiles and sections are not independent donor replicates.

The initial proposed policy requires at least three independent donors per group and 20 retained cells per donor–cell-type combination. These are implementation gates, not guarantees of adequate power. Report exclusions and test sensitivity to the cell threshold. If requirements fail, return descriptive effect estimates and an insufficient-evidence status.

Use PyDESeq2 only for compatible unnormalised integer count inputs \[8\]. Do not round continuous correction outputs merely to force compatibility. Either construct defensible integer counts from retained molecules, adopt and validate a suitable statistical method, or limit that condition to descriptive comparisons. Store the input scale in the analysis metadata.

Freeze the contrast, cell types, gene filters, normalization approach, covariates and method conditions before the primary run. Verify the design matrix is identifiable. Completely confounded study and disease effects cannot be separated by adding a batch covariate. For a small targeted panel, explicitly assess whether normalization assumptions are plausible.

Report effect estimates, uncertainty and donor-level plots. Clearly distinguish shrunken effect estimates from intervals computed for an unshrunk estimator. Define the primary multiple-testing family before running it; record exploratory agent follow-ups separately. FDR adjustment of a growing log is not a guarantee against adaptive selection bias.

## Labels describe evidence rather than biological truth

| **Label**                       | **Proposed operational meaning**                                                                                                                                       |
|---------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Stable across tested conditions | At least two valid conditions; effect direction agrees, between-condition log2 effect range is at most 0.5, and estimable leave-one-donor-out effects retain direction |
| Segmentation sensitive          | At least two valid conditions and an effect reversal or log2 effect range greater than 0.5                                                                             |
| Insufficient evidence           | Too few donors, incompatible inputs, failed diagnostics, unstable donor influence or missing comparisons                                                               |

The 0.5 threshold is a starting design choice, not a validated biological cutoff. Freeze it for the primary analysis and report a small prespecified sensitivity grid. “Stable” does not mean significant or biologically true. Report significance and uncertainty separately. A significance change alone is flagged as threshold sensitivity, not proof of artifact.

Newly significant candidates remain exploratory. Use “confirmed artifact” only where controlled ground truth or independent validation supports that conclusion. When comparing methods, display changes in retained cells, annotation and normalization so a changed result has an interpretable cause.

# 5 Architecture and Meta model integration

## System boundaries

The proposed implementation uses a React interface with a spatial viewer, a Python API for validated analysis tools, and background workers for long jobs. Start with a single project and one worker process; add infrastructure only when needed. Vitessce is a candidate viewer, subject to a small compatibility spike with the selected data.

Keep raw files immutable. Store numerical artifacts in suitable matrix and columnar formats, image pyramids in a viewer-compatible format, and run metadata in a small database. Use OME-Zarr when supported by the chosen image path; do not require a full data conversion before proving the first workflow. GPU tasks may run on Modal, but routine statistics should not depend on a GPU service.

The execution path is: question → approved plan → validated tool calls → versioned artifacts → verification → evidence view → researcher review → export. Tool calls return artifact references and concise summaries rather than sending whole expression matrices to language models.

## Proposed model roles

| **Component**               | **Initial integration**      | **Acceptance evidence**                            |
|-----------------------------|------------------------------|----------------------------------------------------|
| Planner                     | Muse Wonder, muse-wonder-1.0 | Valid plan restricted to available data and tools  |
| Tool worker and explanation | Muse Spark, muse-spark-1.3   | Correct structured calls and grounded explanations |
| Visual review               | Muse Spark on evidence plots | Detects tested plot–claim mismatches               |
| Tissue structures           | SAM, sam-3.1                 | Usable masks on the selected registered images     |
| Optional voice input        | muse-voice-transcribe-1.0    | Correct transcription with editable confirmation   |

These model IDs and broad capabilities appear in Meta’s current documentation \[6\]. Account access, actual endpoint behaviour, rate limits and costs must pass a startup integration check. Store model IDs in configuration and record them per run. If planner access fails, use an available Meta model after capability testing and disclose the substitution. Muse Code is a development tool, not a runtime dependency.

## Reliability built into the first release

Each job has an idempotency key, input hashes, parameters, status, timeout and error record. Persist queued, running, succeeded, failed and cancelled states. Retry transient infrastructure failures with a bounded policy; do not silently retry scientific failure with changed parameters. Cache keys include input, tool, code and configuration versions.

Serve API credentials only from the backend. Treat retrieved papers and dataset text as untrusted content, never as execution instructions. The initial agent uses an allowlisted tool registry; arbitrary generated code execution is outside the first release. Save partial progress so refreshing the interface does not lose the analysis.

# 6 Build contracts and repository structure

## Artifacts shared by every module

**DatasetManifest** holds data provenance, donor metadata, file hashes and capabilities. **AnalysisPlan** holds the question, contrast, methods, testing family, budgets and approval. **ToolRun** holds validated arguments, versions, timestamps, logs and outputs. **Claim** holds an interpretation plus its numerical evidence and verification state. **ReviewDecision** records reviewer, decision, timestamp and claim version.

Every artifact has a schema version and immutable ID. Changing a parameter produces a new run. Verification and human approval are independent fields: a numerically consistent claim can remain unreviewed, and reviewer approval does not repair a failed numerical check.

## Initial tool interfaces

| **Tool**            | **Inputs**                                | **Outputs**                                 |
|---------------------|-------------------------------------------|---------------------------------------------|
| validate\_dataset   | Manifest and file references              | Capability and integrity report             |
| audit\_assignments  | Dataset, condition, frozen score settings | Metrics and flagged region references       |
| compare\_conditions | Dataset, approved plan, condition outputs | Donor-level effects and diagnostics         |
| inspect\_region     | Dataset, region, genes, condition         | Overlay and source artifact references      |
| verify\_claim       | Claim and evidence artifacts              | Check results and failure reasons           |
| export\_analysis    | Run and review state                      | Report, claims, figures and replay manifest |

Add segment\_structures and map\_urine\_candidates behind capability checks. These are proposed interfaces to implement, not existing commands.

## Claim schema example

{  
"schema\_version": "1.0",  
"claim\_id": "claim-example",  
"text": "Generated only from validated evidence",  
"dataset\_id": "dataset-id",  
"analysis\_run\_id": "run-id",  
"contrast\_id": "contrast-id",  
"gene\_id": "measured-gene-id",  
"cell\_type": "reference-label",  
"condition\_ids": \["baseline", "correction"\],  
"statistics\_artifact": "artifact-id",  
"evidence\_status": "insufficient\_evidence",  
"verification\_status": "pending",  
"review\_status": "unreviewed"  
}

The referenced statistics artifact contains effects, interval definitions, adjusted p-values when valid, donor counts and exclusion reasons. Missing values remain null with a reason; a missing p-value must never become zero.

## Suggested repository layout

Use apps/web for the interface, services/api for orchestration, packages/contracts for schemas, analysis for deterministic methods, adapters for external tools and models, evals for fixtures and benchmarks, and configs for frozen plans. Keep raw data outside version control. Version the small manifest, environment lockfiles and reference outputs needed to replay the demo.

# 7 Agent investigation and verification

## A bounded investigation loop

The planner first reads the capability report. It proposes a question-specific plan containing the contrast, tools, expected outputs, budget and stopping conditions. Researcher approval freezes the primary analysis. Any follow-up that changes the contrast or inferential procedure becomes a separately recorded exploratory branch.

The agent may inspect a flagged region, compare supported conditions, examine per-donor effects or request a leave-one-donor-out check. Each choice must cite the observation that motivated it. Missing inputs produce a clear limitation or a request for the specific input; they do not trigger fabricated values or silent substitution of a different dataset.

Proposed initial limits are 12 tool calls and one plan revision per investigation, configurable by the researcher. These are operational controls, not performance claims. On budget exhaustion, the agent returns completed evidence and unresolved questions. It must not choose repeated analyses merely until a favourable p-value appears.

## Four distinct checks

**Structural checks** validate schemas, dataset identity, contrast direction, sample counts and evidence references. **Numerical checks** recompute aggregates from the stored source layer and compare claim values to the result artifacts using declared tolerances. **Visual checks** compare the rendered plot’s labels and direction with the claim. **Scientific review** considers design, confounding and biological plausibility.

Numerical agreement verifies computation consistency, not the truth of the biological interpretation. A second model prompt is not independent ground truth. Initially, implement independent arithmetic checks for sums, group sizes and effect direction; describe full statistical recomputation as implemented only after it has a tested independent path.

A plot-check failure marks the claim as disputed and opens the figure for review. An unavailable check remains unavailable. Confirmed schema or numerical failures block the claim from the validated summary, while preserving it in the diagnostic history. Corrections create a new claim version.

## Provenance and review

Record prompts, model responses, tool versions, seeds, parameters, input and output hashes, timing, model usage and reviewer decisions. Exclude secrets. A local append-only log is sufficient initially; do not claim tamper resistance simply because entries are hash-linked. Stronger integrity guarantees require protecting or externally anchoring the log.

Allow export of work in progress with its review state clearly displayed. A final reviewed report requires an explicit researcher decision. Optional voice commands display an editable transcript and require confirmation for scientific approval or export actions.

**Module acceptance:** a planted direction reversal or wrong sample count is caught; a correct matched claim can pass; an interrupted run resumes without duplicate scientific outputs; and the exported claim points to the exact artifacts that were checked.

# 8 Evaluation and evidence for improvement

## Evaluate the capability actually delivered

Freeze a small benchmark before selecting demonstration examples. Separate development examples from held-out evaluation where feasible. Report all attempted cases, failures, denominators, data versions and conditions. Do not combine results from different datasets into one apparent end-to-end validation.

| **Question**            | **Comparison**                                   | **Evidence to report**                                                |
|-------------------------|--------------------------------------------------|-----------------------------------------------------------------------|
| Does auditing help?     | Baseline versus correction                       | Admixture proxy, signal retention, cells retained, per-sample changes |
| Does SAM help?          | Same workflow with and without SAM contribution  | Independent mask quality or observed inspection benefit               |
| Are findings sensitive? | Prespecified analytical conditions               | Effect changes, donor influence, eligible and excluded findings       |
| Does verification help? | Verification disabled versus enabled             | Error detection and valid-claim rejection                             |
| Is the workflow useful? | Same task with current tools versus SpatialScout | Completion, correctness, elapsed time and interventions               |

## Controlled error benchmark

Begin with at least 20 valid claims and 20 altered counterparts as an engineering target. Include reversed contrast direction, incorrect sample count, wrong dataset reference, changed numerical value and plot-label mismatch. Derive fixtures from real computations, label injected errors explicitly, and keep a held-out subset that was not used to tune the verifier.

Report error-detection rate as detected erroneous claims divided by all erroneous claims, and false-rejection rate as rejected valid claims divided by all valid claims. Show counts by error type; disclose uncertainty with a small benchmark. For deterministic schema and arithmetic fixtures, the release gate is that all expected checks behave correctly. Model-based checks report measured performance rather than inheriting that guarantee.

## Biological and segmentation evaluation

Evaluate masks with independently annotated structures, reporting Dice or IoU and object detection recall, with counts of donors, slides and objects. Split by donor when known and otherwise by slide, never random overlapping tiles. Evaluate staining or cohort transfer separately. Fine-tuning and prompt selection use training or validation data, not the final test set.

For sensitivity rates, define the denominator before inspection: for example, all baseline findings passing a prespecified filter that have valid alternative-condition estimates. Report excluded findings separately. A count of sensitive findings is not a count of false discoveries. Preserve stable and negative examples alongside dramatic changes.

## Researcher evaluation

If researchers are available, use the same task, a clear completion definition and observed timing. Record prior familiarity and manual assistance. Keep observed durations separate from estimates of usual workflow time. Rate claims as supported, plausible, unsupported or unassessable; report those categories separately. Obtain permission for attributed quotations and do not imply institutional endorsement.

# 9 Implementation sequence and time gates

## Start with the smallest complete path

Build in dependency order: M0 → M1 → M2, while strengthening M3 throughout. The first vertical implementation should validate one dataset, answer one supported question, execute one audit, display one evidence view and export one provenance-linked result. Only then expand methods or datasets.

The initial engineering tasks are to establish the repository and schemas; inventory the candidate data; run a small correction-tool smoke test; make one successful Meta structured-output call; and connect the outputs to a simple viewer. Write focused tests for donor aggregation, input rejection, claim direction and reproducible artifact identity.

## Proposed sprint beginning November 2

| **Window**         | **Deliverable**                              | **Decision at the gate**                                  |
|--------------------|----------------------------------------------|-----------------------------------------------------------|
| First 2 hours      | Data and model capability probes             | Choose supported dataset and workflow                     |
| Next 6 to 8 hours  | Integrated M1 with basic verification        | Continue only after question-to-export works              |
| Next 6 to 10 hours | M2 or stronger audit evaluation              | Prefer a defensible result over an unsupported comparison |
| Next 4 to 6 hours  | Controlled benchmark and researcher feedback | Fix highest-impact failures                               |
| Final 6 to 8 hours | Freeze, rehearse, record and package         | No new major modules                                      |

These are planning allocations, not estimates established by a working implementation. Adapt them to actual hours and staffing. The public event page lists November 4 at 9 PM Eastern for submission, equivalent to 8 PM Chicago time on that date \[9\]. Use the participant portal’s current requirements as the final authority and reserve time before the deadline.

## Explicit fallback decisions

If cohort images remain unavailable, ship coordinate inspection and keep SAM image analysis clearly separate. If correction inputs or count semantics fail, ship an audit-only workflow. If replication is insufficient, show descriptive evidence rather than disease p-values. If model access fails, use a tested available Meta model and record the change. If an optional component threatens the working path, defer it.

The minimum build does not depend on fine-tuning, multi-omics integration or voice. Those remain part of the platform roadmap. A completed improvement can be added after the core release passes its checks.

## Completion means evidence exists

For each module, maintain planned, in progress, demonstrated and evaluated states. “Demonstrated” requires a successful run on real data. “Evaluated” additionally requires recorded benchmark results. Store the run IDs and artifacts supporting each state. Dated commits establish build history; do not claim work occurred during the event without that evidence.

# 10 Demonstration and submission package

## A short narrative with a visible consequence

Open with the researcher’s decision: which candidate deserves follow-up? Briefly establish that cell assignments can affect the evidence. Ask the agent a question supported by the loaded dataset, inspect a flagged region, and show the relevant result across conditions. Explain whether the evidence is stable, sensitive or insufficient.

Show what the researcher can now do: inspect a questionable assignment, prioritize a stable candidate, or identify the next experiment needed. Demonstrate one clearly labelled injected claim error and the verification response. Finish by opening the exported evidence package and showing how to reproduce the result.

Use a real observed improvement if available. If no biological improvement is established, demonstrate an actual gain in task completion, error detection or evidence accessibility. Do not script a disappearing disease signal before the analysis has produced it.

## Recommended demo structure

| **Segment**          | **What appears on screen**                  | **Evidence requirement**                    |
|----------------------|---------------------------------------------|---------------------------------------------|
| Problem and question | Dataset and researcher task                 | Accurate modality and donor labels          |
| Investigation        | Agent plan and tool progress                | Actual calls or clearly labelled replay     |
| Result               | Region, donor plot and condition comparison | Linked artifacts and uncertainty            |
| Verification         | Deliberately altered claim rejected         | Injection labelled, valid control available |
| Research decision    | Review and export                           | Recorded decision and reproducible package  |

Use this as a roughly three-minute narrative unless the submission rules specify another duration. Keep a longer technical walkthrough available. Cached preprocessing is acceptable when disclosed; distinguish cached numerical results from live agent reasoning and from a full raw-data rerun.

## Package contents

Provide the repository with environment locks, source attributions and configuration; a README distinguishing implemented features from roadmap; an accessible demonstration or recorded walkthrough; a small reproducible example where redistribution permits; and an evaluation report with raw counts, failures, data versions and costs.

Implement a replay entry point and a separate raw-data rerun entry point, then document their actual commands and dependencies. A replay proves artifact accessibility; a raw-data rerun tests computational reproducibility. Measure model usage and compute costs from logs instead of promising a fixed low cost in advance.

## Explain the innovation precisely

Credit published segmentation and correction methods. Describe SpatialScout’s own contributions as the investigation policy, data capability checks, evidence labels, linked viewer, verification implementation and researcher workflow. Demonstrate any new scientific method separately. For the indie track, connect creativity, technical ambition and working behaviour to concrete evidence; the public page does not provide detailed prize weights \[9\].

# 11 Expansion into the full platform

## Tissue to urine and additional omics

Add urine-protein exploration after the spatial evidence workflow is reliable. Begin with a curated protein-to-gene mapping and visible source references. Display where the corresponding transcripts are observed, subject to panel coverage. Describe this as a candidate tissue association: RNA expression alone does not establish secretion, urinary abundance or causal tissue origin.

Cross-study or unmatched cohorts support exploratory concordance only. Paired measurements, independent replication and experimental validation are required for stronger biomarker claims. Extend the same provenance contracts to spatial proteomics and other modalities, with modality-specific quality checks. Do not apply molecule-assignment assumptions unchanged to multicellular Visium spots.

## Model adaptation

Fine-tune a segmentation model only after weight access, annotation terms, checkpoint compatibility and compute requirements are verified. Meta’s SAM repository includes inference and training resources, but a specific training recipe must be matched to the chosen checkpoint \[7\]. Record the checkpoint and code revision. Do not promise a particular frozen-layer recipe or training budget before a measured trial.

Compare an adapted model with appropriate stock prompting baselines on held-out donors or slides. Include manual prompt effort in the comparison. Keep a successful stock-model workflow as a fallback. Voice input and additional agent roles should be added when they improve an observed researcher task.

## Risks and corresponding design responses

| **Risk**                                      | **Design response**                                              |
|-----------------------------------------------|------------------------------------------------------------------|
| Genuine biology mistaken for contamination    | Preserve uncertainty, independent controls and researcher review |
| Lower proxy score from deleting signal        | Report retention and stable biological controls together         |
| Few donors or confounded cohorts              | Restrict inference and show per-donor evidence                   |
| Model invents a number or source              | Structured claims, artifact references and deterministic checks  |
| Fine-tuning does not transfer across stains   | Separate transfer evaluation and maintain stock baseline         |
| Missing data or unreliable external services  | Capability gates, resumable jobs and disclosed replay            |
| Platform expands faster than it can be tested | Require a working complete task before adding a major module     |

## Long term outcome

SpatialScout aims to become a daily workspace for defensible spatial research. Researchers should be able to ask a question, see how analytical choices affect the answer, review the supporting evidence and reproduce the work. Multi-lab evaluation can later establish generality, usability and practical impact.

The immediate development objective is narrower and measurable: complete one real investigation with transparent assumptions, working tools and reviewable evidence. Each additional module extends that capability while preserving the same scientific and engineering contracts.

# 12 References and implementation sources

The numbered references support the background and integration choices. Thresholds, release gates, schemas and sprint allocations in this document are proposed design decisions rather than published validation results. Recheck data terms and provider documentation when pinning the implementation.

**1. Mitchel J and colleagues.** Impact and correction of segmentation errors in spatial transcriptomics. Nature Genetics 58, 434–444 (2026). DOI: 10.1038/s41588-025-02497-4.

https://www.nature.com/articles/s41588-025-02497-4

**2. Kharchenko laboratory.** cellAdmix source code, installation and tutorials. Used as a candidate published correction baseline, with a pinned revision and explicit attribution.

https://github.com/kharchenkolab/cellAdmix

**3. NCBI Gene Expression Omnibus.** GSE286184, Single-nucleus transcriptomic landscape of human glomerular diseases, Xenium series. Candidate cohort; donor mapping and required files must pass ingestion checks.

https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE286184

**4. NCBI Gene Expression Omnibus.** GSM8720413 sample record. Protocol describes a targeted panel; verify the actual features across selected samples.

https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSM8720413

**5. 10x Genomics.** Human Kidney Preview Data, Xenium Human Multi-Tissue and Cancer Panel. Candidate visual integration dataset; non-diseased and PRCC specimens, two donors, CC BY 4.0.

https://www.10xgenomics.com/datasets/human-kidney-preview-data-xenium-human-multi-tissue-and-cancer-panel-1-standard

**6. Meta.** Meta Model API model catalogue. Model names, identifiers and broad hosted capabilities checked November 2, 2026.

https://dev.meta.ai/docs/models

**7. Meta.** SAM source repository, checkpoint release notes and training resources. Verify training support against the exact revision selected.

https://github.com/facebookresearch/sam3

**8. PyDESeq2.** Official documentation. Candidate count-based differential-expression implementation; validate input assumptions and freeze its version.

https://pydeseq2.readthedocs.io/en/stable/

**9. Cerebral Valley and Meta.** Meta Global AI Developer Hackathon event page. Public tracks, themes and submission schedule checked November 2, 2026.

https://cerebralvalley.ai/e/meta-ai-developer-hackathon
