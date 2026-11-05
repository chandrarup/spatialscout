# Research-delegation opportunities for SpatialScout

Checked 2026-11-04. This note separates external scientific motivation, capabilities reported by the current repository, and proposed additions. It is not a validation of the app's biology or an independent rerun of its results.

## Recommended public explanation

**SpatialScout is a Meta-powered spatial co-scientist for kidney disease research. It helps researchers investigate an unexpected signal in tissue, test alternative explanations, compare available RNA and protein evidence, and prepare a traceable report for their next experiment.**

Start the demonstration with the human problem: *“A kidney researcher sees an unexpected molecular signal. Before spending effort on a follow-up experiment, they need to know where it comes from and how dependable it is.”* Show a tissue region, delegate the investigation, reveal the controls and evidence, and end with the next experiment the researcher can choose. Gene symbols can appear after this explanation.

This is a proposed presentation, not a claim that SpatialScout measures experimental value or has established a new kidney mechanism. The strongest defensible completed task is **investigating the robustness of an unexpected cellular signal**. Discovering disease mechanisms and selecting treatments require additional data and experiments.

## Disease and data coverage: say this explicitly

The repository's current `README.md`, `docs/research/data-readiness.md`, and `CLAUDE.md` report:

- **RNA:** GSE286184 human kidney: controls, diabetic kidney disease (DKD), IgA nephropathy (IgAN), minimal change disease (MCD), and membranous nephropathy (MN). Twenty-two deposited sections include one duplicate, giving 21 distinct sections. There are 50 measured genes. Author cell-type annotations and morphology images were not deposited; the app supplies its own marker-rule labels and RNA renderings.
- **Protein microscopy:** four separate KPMP CODEX biopsies: two Healthy Reference, one CKD, one AKI. CKD is a broad enrollment category; it does not establish DKD or lupus nephritis. The frozen lab cross-check uses one healthy reference and one CKD participant.
- **Lupus nephritis (LN):** no current LN cohort is established by these sources. Say **“LN is a future application”**, not “we analyse LN today.”
- **RNA/protein relationship:** these are different datasets and participants. A protein pattern in KPMP is a separate corroborative observation, not matched same-cell or same-patient RNA/protein validation. No registered overlay of GSE286184 RNA on KPMP microscopy is justified.
- **Inference:** section-to-donor mapping is unavailable in GSE286184, so contrasts are descriptive, with no inferential p-values. Persistence under stricter assignment does not prove biological origin. KPMP masks, thresholds and between-run calibration have limitations already documented in README.

Dataset record: [GSE286184](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE286184). Details above are based on the repository's prior downloads/metadata inspections; the public GEO HTML returned a CAPTCHA in this research pass.

Suggested opening title: **“SpatialScout — a spatial co-scientist for kidney disease research”**. Subline: **“Demonstrated on human kidney RNA data including DKD, and separate healthy/CKD/AKI protein images.”**

## Difficult questions scientists could delegate

| Research question | Why it matters | Credible current demonstration | Future module needed |
| --- | --- | --- | --- |
| “Does this unexpected signal survive plausible changes in which molecules belong to a cell?” | Assignment errors can affect downstream biological interpretation. | Existing assignment audit, random-thinning controls, label-sensitivity checks, region evidence and verifier. | Independently benchmark alternative segmentation/reassignment tools; measure purity and coverage together. |
| “Can I see supporting protein evidence, and what disagrees?” | RNA observations and protein measurements give different evidence; specimen identity and assay limitations matter. | Existing separate KPMP image inspection and protein audit, with explicit separate-specimen labels. | Matched or serial-section ingestion, registration quality checks, channel/threshold calibration, same-cell association where justified. |
| “Which injured tubules sit next to immune or fibrotic tissue?” | Spatial neighborhoods can distinguish disease-associated contexts that bulk expression misses. | Show existing cell/gene/protein maps and descriptive supported features. | Formal neighborhood enrichment, spatial null models, donor-aware replication, robust cell-state annotation and a richer panel. |
| “Which observations deserve an experiment, given the evidence and conflicting papers?” | Interpretation requires locating evidence, checking alternatives and identifying missing tests. | Existing cited literature agent, verified results, figure export and proposed next experiments. | Comparative reviewer evaluation; experiments and measured outcomes, not model confidence alone. |
| “Can you analyse this huge microscopy file and expression table without losing coordinates or provenance?” | Formats, scales, coordinate transforms and chunking are engineering/scientific failure points. | Curated KPMP tiles and existing transcript/cell upload workflow. | OME-TIFF/OME-Zarr readers, streaming tiling, spatial transforms, resumable jobs, registered metadata, modality-specific QC. |

### 1. Assignment uncertainty is a substantive problem

A primary Nature Methods benchmark published **23 October 2026** assessed 11 segmentation methods across 15 datasets and five technologies. It found that segmentation choice affects cell-type specificity, transcript contamination and ligand–receptor inference. It also identifies format incompatibility, coordinate alignment and large-data patch processing as practical obstacles. Performance depends on dataset and evaluation criterion, so a visually convincing mask is insufficient. This supports a domain harness that evaluates consequences and records evidence; it does not establish that SAM 3.1 or SpatialScout is universally best. [Benchmarking segmentation methods for spatial transcriptomics](https://www.nature.com/articles/s41592-026-03272-x).

Related primary work introduced cellAdmix to address segmentation-related transcript mixing. Existing correction methods are part of the field, so avoid presenting assignment auditing as a novel scientific discovery. The contribution can be making checked investigations accessible and reproducible through an agentic workflow. [Impact and correction of segmentation errors in spatial transcriptomics](https://www.nature.com/articles/s41588-025-02497-4).

### 2. Kidney spatial neighborhoods provide the broader scientific ambition

An April 2026 human DKD study combined spatial and single-nucleus data to characterize injury-associated neighborhoods and a B-cell-rich subgroup associated with progression. This motivates questions about immune–epithelial–fibrotic context and patient heterogeneity. Its richer datasets and validated results must not be attributed to SpatialScout's 50-gene cohort. [Spatial atlas of diabetic kidney disease reveals a B cell-rich subgroup](https://www.nature.com/articles/s41586-026-10363-4).

A human LN study combined single-cell multiome, spatial transcriptomics and validation experiments, identifying VCAM1-expressing proximal-tubule cells in an inflammatory/fibrotic niche. An appropriate future question is: *“Where are injury-associated tubules, which immune/fibroblast populations surround them, and does the association replicate across patients?”* Answering it requires an actual LN cohort, adequate markers, suitable controls and independent validation. [Integrative spatial multiomics analysis reveals regulatory mechanisms of VCAM1+ proximal tubule cells in lupus nephritis](https://doi.org/10.1016/j.ard.2025.08.015).

### 3. Large-image analysis needs a data system, not a larger prompt

SpatialData provides a common representation for images, labels, points, shapes and tables, with coordinate transformations and efficient multiscale/chunked storage. This is an appropriate foundation to evaluate for future multi-assay ingestion, not an implemented feature inferred from having a viewer. [SpatialData primary publication](https://pmc.ncbi.nlm.nih.gov/articles/PMC11725494/).

OME's NGFF specification represents multidimensional multiscale images with space and optional time/channel axes. OME also explains that chunking avoids downloading an entire image to inspect a region. For a large TIFF, plan computational tiling and coordinate-preserving retrieval; send selected crops/derived summaries to vision models while quantitative tools process the original data. Do not imply a model directly understands an arbitrary complete multigigabyte file. [NGFF specification](https://ngff.openmicroscopy.org/latest/), [OME help desk](https://ngff.openmicroscopy.org/help-desk/index.html).

## What makes the harness more than a conversational wrapper

The defensible distinction is the implemented coupling of **data capability checks, domain tools, selected controls, reproducible quantitative computation, evidence provenance, claim verification, and human review**. The model is responsible for proposing and interpreting actions inside these boundaries. A generic model with equally good tools could in principle reproduce the workflow; comparative superiority requires a benchmark.

A range of Meta models provides distinct roles for planning, interpretation, image/figure inspection, segmentation assistance and voice. This is an architectural advantage for composing the workflow, not evidence that Meta is more scientifically accurate than another provider. SAM's current RNA-derived outlines remain exploratory, and a visual LLM check is fallible; the README reports valid co-expression claims disputed by that check.

## Honest effort-reduction demonstration

Show the manual tasks being delegated: locate a suspicious region → prepare repeated count analyses → select and run controls → inspect separate protein evidence → retrieve papers → check and export the report. Say “brings these steps into one workflow” or “reduces the manual coordination required.” Do not invent an hours-to-minutes reduction. To measure it, predefine the same task, inputs and acceptable deliverables; time researcher completion manually and with the app, record interventions/errors and have another reviewer judge correctness. Report actual measurements, not estimates as achieved results.

## Retrieval provenance

The segmentation benchmark and DKD atlas were accessible as full Nature HTML during this pass. Their primary abstracts were also accessible on PubMed: [segmentation PMID 42919952](https://pubmed.ncbi.nlm.nih.gov/42919952/) and [DKD PMID 42056516](https://pubmed.ncbi.nlm.nih.gov/42056516/). The LN publisher page failed direct opening, but primary publisher and [PubMed PMID 40973516](https://pubmed.ncbi.nlm.nih.gov/40973516/) search results returned the complete abstract; LN claims above are limited to that abstract. Direct opening of this LN PubMed record returned only a footer, so this pass does not establish full-paper access. Some Nature and NCBI accesses were intermittent or blocked on other calls.
