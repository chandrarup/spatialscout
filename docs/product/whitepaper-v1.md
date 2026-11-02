> Generated from `SpatialScout Whitepaper.docx` (Oct 28, 2026) with pandoc so agents can read it. The .docx is canonical. Superseded on scientific claims by build-whitepaper-v2.md.

# SpatialScout: Trustworthy Disease Discovery in Spatial Biology

Oct 28, 2026 · @Chandra rup

> **Draft status.** Every result, metric and lab comment marked **\[TO MEASURE\]** or **\[PENDING\]** is a placeholder. Replace each one with the measured value or the real quote before submission, then delete this note.

## Abstract

SpatialScout is an agentic analysis platform that tells kidney researchers which differences between diseased and healthy tissue are real. Spatial transcriptomics measures gene expression cell by cell inside intact biopsies, but every downstream result depends on cell segmentation, and segmentation errors can dominate those results.

SpatialScout audits segmentation first. It then compares diseased and healthy tissue, links tissue findings to urine proteomics, and returns hypotheses that a verifier has recomputed and a principal investigator (PI) has approved. Scientists drive the whole analysis in plain language or by voice.

The platform runs on Meta's models. Muse Wonder plans each analysis, Muse Spark 1.3 runs and verifies the steps, SAM 3.1 (fine-tuned on kidney glomeruli) segments tissue structures, and Muse Voice Transcribe takes spoken commands.

We evaluate SpatialScout on public human kidney datasets covering four glomerular diseases and lupus nephritis. Baselines are current segmentation methods and contamination-correction tools, and researchers in a university lupus nephritis lab test the platform. Headline results:

-   Contamination reduced from **\[TO MEASURE\]** to **\[TO MEASURE\]** versus default segmentation.

-   **\[TO MEASURE\]**% of default-segmentation disease findings flagged as segmentation artifacts.

-   Glomerulus segmentation Dice raised from **\[TO MEASURE\]** (stock SAM 3.1) to **\[TO MEASURE\]** (fine-tuned).

-   Lab researchers rated **\[PENDING\]** of **\[PENDING\]** agent claims correct or plausible.

SpatialScout is a research tool. It makes no diagnoses and no patient-level predictions.

## 1. The problem: segmentation errors hide inside disease findings

Spatial transcriptomics can show which cells change in disease, but segmentation errors can decide the answer. Segmentation assigns each detected RNA molecule to a cell; when a molecule lands in the wrong cell, that cell looks like something it is not.

A 2026 *Nature Genetics* study by Mitchel, Kharchenko and colleagues reanalysed spatial datasets across tissues and platforms. Misassigned molecules distorted differential expression, estimates of how neighbouring cells influence each other, and ligand–receptor predictions, often more than the real biology did ([Mitchel et al. 2026](https://www.nature.com/articles/s41588-025-02497-4); [summary](https://www.rna-seqblog.com/impact-and-correction-of-segmentation-errors-in-spatial-transcriptomics/)). The authors released a correction tool, [cellAdmix](https://github.com/kharchenkolab/cellAdmix).

Disease-versus-healthy comparisons are especially exposed. Disease changes which cells sit next to which: in lupus nephritis, immune cells infiltrate glomeruli and sit against podocytes and endothelial cells. Contamination then differs between the two groups, and a segmentation artifact becomes a "disease signature".

The stakes in lupus nephritis are high. In an international inception cohort of 1,827 people with lupus, 38.3% developed nephritis, and the 10-year risk of end-stage kidney disease was 10.1% with nephritis versus 4.3% overall ([Hanly et al. 2016](https://escholarship.org/uc/item/5s98z3vv)). Patients with nephritis were younger and more often men, and more often of African, Asian or Hispanic ancestry.

The gap is a working tool, not another method. Segmenters and correction tools exist, but no platform lets a lab audit segmentation, compare disease with healthy tissue, connect the result to other omics and record every decision in one daily workflow.

## 2. SpatialScout at a glance

SpatialScout is where a kidney lab runs its spatial analysis day to day: one workspace that checks segmentation before any result is trusted. It serves three people:

-   **Research scientists and trainees** who run the analyses and need answers they can defend.

-   **PIs** who decide which findings deserve months of follow-up work.

-   **Translational teams** who turn tissue findings into biomarker and target hypotheses.

| Daily task                          | Today                                                                     | With SpatialScout                                                                    |
|-------------------------------------|---------------------------------------------------------------------------|--------------------------------------------------------------------------------------|
| Check segmentation quality          | Eyeball overlays, or skip the check                                       | Contamination score per cell and per method, flagged on the slide                    |
| Compare diseased and healthy tissue | Custom scripts per project; cells often treated as independent replicates | Sample-level comparison; each finding labelled robust, artifact or newly revealed    |
| Connect tissue to urine proteomics  | Manual lookups across papers and spreadsheets                             | Each urine protein mapped to the cells and structures that express it                |
| Explain a result to the PI          | Static figures pasted into slides                                         | Interactive viewer; every claim linked to its plot, its numbers and its verification |
| Reproduce last month's analysis     | Rerun old notebooks, if they still run                                    | Audit log and exported notebook replay every step                                    |

Time for one end-to-end disease comparison: **\[TO MEASURE\]** with SpatialScout, versus the lab's estimate of **\[PENDING\]** by hand.

## 3. How it works

A question goes in; audited, verified and approved findings come out. Each step is a checkpoint the PI can open and inspect.

<img src="media/image1.png" style="width:6in;height:5.24107in" alt="SpatialScout analysis flow · 6 steps, 1 loop" />

SpatialScout analysis flow · 6 steps, 1 loop

The audit in step 2 and the verifier in step 5 make the output trustworthy: a finding reaches the PI only after passing both, and a claim that fails verification goes back for reanalysis.

## 4. Built on Meta's models

Every AI call in SpatialScout goes to a Meta model, and each model does a distinct job.

| Model                                                     | Role in SpatialScout                                                                                               | Why this model                                                                                                                    |
|-----------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------|
| [Muse Wonder](https://dev.meta.ai/models/muse-wonder)     | Planner: turns a scientist's question into a checkpointed analysis plan and hands steps to workers                 | Built for long-running agents that plan, delegate to sub-agents, call tools in parallel and recover from errors; 1M-token context |
| [Muse Spark 1.3](https://dev.meta.ai/models/muse-spark)   | Workers that call analysis tools; verifier that recomputes numbers and reads each plot                             | Trained for agentic workflows with reliable tool calling; reads images, video and documents natively                              |
| [SAM 3.1](https://dev.meta.ai/models/sam-3-1), fine-tuned | Segments glomeruli, tubules, vessels and immune aggregates from text prompts; masks become boundaries in the audit | Detects and returns pixel-precise masks from a short noun phrase, zero-shot, and tracks objects through video with identity kept  |
| Muse Voice Transcribe                                     | Hands-free commands and checkpoint approvals at the bench                                                          | Speech to text on the same Meta Model API                                                                                         |
| Muse Code                                                 | Coding agent used to build parts of the platform **\[CONFIRM before submission\]**                                 | Meta's agentic coding tool                                                                                                        |

Three uses go beyond a standard integration:

1.  **A model that checks itself.** The verifier sends Muse Spark 1.3 the rendered plot behind each claim and asks whether the plot shows what the claim says. A claim whose plot disagrees is flagged, even when its text sounds right.

2.  **SAM 3.1 taught kidney pathology.** We fine-tune SAM 3.1 on public glomerulus annotations and report stock versus fine-tuned accuracy on held-out slides (Appendix E).

3.  **Video tracking repurposed for slides (stretch goal).** Whole-slide tiles stream to SAM 3.1 as frames of a video, so each glomerulus keeps one identity across tile seams.

Cost stays low. Spark 1.3 costs $1.25 per million input tokens and $4.25 per million output tokens, and SAM 3.1 costs $2.50 per 1,000 images ([Meta pricing](https://dev.meta.ai/models/muse-spark), [SAM 3.1](https://dev.meta.ai/models/sam-3-1)). Measured API cost per full analysis: **\[TO MEASURE\]**.

## 5. Evaluation design

We test SpatialScout against current tools on five questions, each answered with a number. Datasets, licences and exact formulas are in Appendices B to D.

| Question                                           | Compared against                                                                                                    | Metric                                                                                                                                   |
|----------------------------------------------------|---------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------|
| Does the audit reduce contamination?               | 10x default segmentation, Proseg, Cellpose-SAM; corrections cellAdmix and [2DE](https://iclr.cc/virtual/2025/35939) | Rate of cells expressing marker pairs that never co-occur in the matched single-nucleus reference; transcripts assigned; cells recovered |
| Does it change disease-versus-healthy conclusions? | Same disease comparison run on default segmentation                                                                 | Share of top default findings labelled artifacts; counts of robust and newly revealed findings                                           |
| Does fine-tuning SAM 3.1 help?                     | Stock SAM 3.1 with a text prompt; stock SAM 3.1 with box prompts                                                    | Glomerulus Dice, IoU and detection F1 on held-out slides                                                                                 |
| Does the agent tell the truth?                     | Known published findings; deliberately planted false claims                                                         | Recall of known findings; share of planted false claims the verifier catches                                                             |
| Is it useful to scientists?                        | The lab's current workflow                                                                                          | Researcher ratings of agent claims, time per analysis, API cost (Section 7)                                                              |

**Positive controls.** An honest system must rediscover what is already known before its new findings deserve trust:

1.  **Morphology agrees with molecules.** Podocyte markers (NPHS1, NPHS2, PODXL) should be enriched inside predicted glomeruli, and tubule markers (LRP2, UMOD) inside predicted tubules.

2.  **Urine chemokines trace to infiltrating immune cells.** In lupus nephritis, the AMP network linked a urinary chemokine gradient to production by kidney-infiltrating myeloid, NK and CD8 T cells; in six matched patients, the urine signal tracked CD8 T-cell abundance in the biopsy ([Fava et al. 2020](https://www.medrxiv.org/content/10.1101/2020.03.13.20034348v1)).

3.  **Urine biomarkers have tissue sources.** An aptamer screen of more than 1,100 urine proteins found markers such as VCAM-1 and ALCAM that separated active nephritis from inactive lupus ([Stanley et al. 2020](https://www.nature.com/articles/s41467-020-15986-3); [summary](https://mdedge.com/content/proteins-urine-may-predict-active-lupus-nephritis)). SpatialScout should place each one in the cells and structures that express it.

**Statistical guardrails.** Disease comparisons use samples, not cells, as replicates, with false discovery rate control and effect sizes with confidence intervals. With few samples per group, every finding is reported as a hypothesis with its effect size, not as a discovery.

## 6. Results

**\[TO MEASURE\]** Lead with the single most important number here, in one sentence: the share of default-segmentation disease findings that the audit shows to be artifacts.

**Table 1. Segmentation audit** on **\[TO MEASURE: n control, n disease\]** human kidney biopsies (GSE286184).

| Method                  | Contamination rate (%) | Transcripts assigned (%) | Cells recovered | Runtime per sample |
|-------------------------|------------------------|--------------------------|-----------------|--------------------|
| 10x default             | \[TO MEASURE\]         | \[TO MEASURE\]           | \[TO MEASURE\]  | \[TO MEASURE\]     |
| Proseg                  | \[TO MEASURE\]         | \[TO MEASURE\]           | \[TO MEASURE\]  | \[TO MEASURE\]     |
| Cellpose-SAM            | \[TO MEASURE\]         | \[TO MEASURE\]           | \[TO MEASURE\]  | \[TO MEASURE\]     |
| 10x default + cellAdmix | \[TO MEASURE\]         | \[TO MEASURE\]           | \[TO MEASURE\]  | \[TO MEASURE\]     |
| SpatialScout audit      | \[TO MEASURE\]         | \[TO MEASURE\]           | \[TO MEASURE\]  | \[TO MEASURE\]     |

**Table 2. Disease-versus-healthy findings** (top findings per cell type under default segmentation, relabelled by the audit).

| Comparison                          | Top default findings | Artifacts (%)  | Robust         | Newly revealed |
|-------------------------------------|----------------------|----------------|----------------|----------------|
| Diabetic kidney disease vs control  | \[TO MEASURE\]       | \[TO MEASURE\] | \[TO MEASURE\] | \[TO MEASURE\] |
| IgA nephropathy vs control          | \[TO MEASURE\]       | \[TO MEASURE\] | \[TO MEASURE\] | \[TO MEASURE\] |
| Minimal change disease vs control   | \[TO MEASURE\]       | \[TO MEASURE\] | \[TO MEASURE\] | \[TO MEASURE\] |
| Membranous nephropathy vs control   | \[TO MEASURE\]       | \[TO MEASURE\] | \[TO MEASURE\] | \[TO MEASURE\] |
| Lupus nephritis vs control (Visium) | \[TO MEASURE\]       | \[TO MEASURE\] | \[TO MEASURE\] | \[TO MEASURE\] |

**Table 3. Glomerulus segmentation** on held-out slides.

| Model                              | Dice           | IoU            | Detection F1   |
|------------------------------------|----------------|----------------|----------------|
| Stock SAM 3.1, text prompt         | \[TO MEASURE\] | \[TO MEASURE\] | \[TO MEASURE\] |
| Stock SAM 3.1, box prompts         | \[TO MEASURE\] | \[TO MEASURE\] | \[TO MEASURE\] |
| Fine-tuned SAM 3.1 (PAS, held-out) | \[TO MEASURE\] | \[TO MEASURE\] | \[TO MEASURE\] |
| Fine-tuned SAM 3.1 (H&E transfer)  | \[TO MEASURE\] | \[TO MEASURE\] | \[TO MEASURE\] |

**Agent truthfulness and cost.** Positive controls recovered: **\[TO MEASURE\]** of 3. Planted false claims caught by the verifier: **\[TO MEASURE\]** of **\[TO MEASURE\]**. Plot–claim mismatches flagged: **\[TO MEASURE\]**. Median API cost per full analysis: **\[TO MEASURE\]**.

**Figure \[PENDING\].** One glomerulus under default and audited segmentation, side by side, with the contaminated cells highlighted and the disease finding that disappears.

## 7. Lab validation

Researchers in a university lupus nephritis lab used SpatialScout on public data and rated its output; their verdict is reported here unedited.

**Protocol**

1.  **Participants:** the lab's PI and **\[PENDING\]** lab members. Each consented to being recorded and quoted; feedback is personal, not an institutional endorsement.

2.  **Data:** public datasets only. No unpublished or patient data appeared on screen.

3.  **Task:** "Find what differs between lupus nephritis and healthy glomeruli, and tell me which differences survive the segmentation audit."

4.  **Rating:** each participant rated **\[PENDING: 10\]** agent claims as correct, plausible or wrong, and marked any claim worth following up.

5.  **Time:** each estimated how long the same question takes in their current workflow.

6.  **Feedback:** each named one improvement. We built the top request before submission and logged the change.

| Measure                                       | Result                        |
|-----------------------------------------------|-------------------------------|
| Claims rated correct                          | \[PENDING\]                   |
| Claims rated plausible                        | \[PENDING\]                   |
| Claims rated wrong                            | \[PENDING\]                   |
| Claims marked worth following up              | \[PENDING\]                   |
| Time with SpatialScout (median)               | \[PENDING\]                   |
| Estimated time with current workflow (median) | \[PENDING\]                   |
| Would use it weekly                           | \[PENDING: yes / no, n of n\] |

**PI comment**

> "\[PENDING: quote, used with permission\]" — Principal Investigator, university lupus nephritis lab

**Lab member comments**

> "\[PENDING\]" — Lab member

**Change shipped from feedback:** **\[PENDING: the request\]** → **\[PENDING: what we built and when\]**.

## 8. Impact and path forward

SpatialScout shortens the path from a biopsy to a hypothesis a lab can trust, and three downstream efforts depend on that path.

**Biomarker discovery.** Kidney biopsies are invasive and cannot be repeated often, so the field wants urine markers that reflect what happens in tissue ([Stanley et al. 2020](https://mdedge.com/content/proteins-urine-may-predict-active-lupus-nephritis)). SpatialScout ties each candidate urine protein to the cells and structures that make it, after removing segmentation artifacts, so the candidates a lab validates rest on real tissue biology.

**Target prioritisation.** A finding that survives the audit and has a clear cellular source is a better starting point for drug work. The AMP urine study, for example, traced its chemokine signal to IFN-γ-producing infiltrating cells and argued for studying IFN-γ inhibition in lupus nephritis ([Fava et al. 2020](https://www.medrxiv.org/content/10.1101/2020.03.13.20034348v1)). SpatialScout makes that kind of source tracing routine.

**Clinical trial research.** The same authors argued that tracking active disease pathways could better inform treatment selection and patient selection for trials. Audited, sample-level tissue signatures are the raw material for that stratification research.

**Beyond lupus.** Nothing in the pipeline is specific to one disease. Our evaluation already covers four other glomerular diseases, and the same audit applies to any spatial dataset with a matched single-cell reference, from neurodegeneration to tumour biology.

**Next steps**

1.  Run SpatialScout on newly released lupus nephritis Xenium cohorts as they become public.

2.  Add spatial proteomics and imaging mass cytometry as further omics layers.

3.  Open the audit metrics as a standalone package so any lab can score its own segmentation.

4.  Run a multi-lab study measuring time saved and agreement with expert annotation.

## 9. Responsible use and limitations

SpatialScout is a research tool for scientists, never a clinical one.

-   **No medical advice.** It makes no diagnoses, no patient-level predictions and no treatment suggestions. Every output is a research hypothesis that a scientist must review, and the interface says so on every screen.

-   **People decide.** The agent proposes; a PI approves each checkpoint, and every decision is logged with who made it.

-   **Public data only.** All datasets are public and cited (Appendix B). No unpublished lab data or patient data is used.

-   **Small samples.** Public cohorts have few samples per group, so findings carry effect sizes and confidence intervals and are framed as hypotheses.

-   **Cross-study comparisons.** Lupus nephritis biopsies and controls sometimes come from different studies, which mixes biology with batch effects. We flag these comparisons and prefer within-study ones.

-   **Model limits.** Language models can state wrong things fluently. The verifier recomputes every number and checks every plot, but it reduces this risk rather than removing it; experts still review.

-   **Segmentation is never perfect.** The audit measures and reduces contamination; it cannot guarantee a correct boundary for every cell.

## 10. Conclusion

Spatial biology can show what changes when a kidney becomes diseased, but only if each molecule is counted in the right cell. SpatialScout makes that check part of every analysis: it audits segmentation, separates real disease differences from artifacts, links them to urine proteomics, and hands the PI verified, traceable hypotheses. Built on Meta's models, with SAM 3.1 fine-tuned for kidney tissue, it turns a slow expert workflow into one a lab can run every day. **\[TO MEASURE: close with the headline artifact rate and the lab's rating.\]**

## Technical appendix

This appendix gives reviewers what they need to check and reproduce SpatialScout: the architecture, data and licences, metric definitions, statistics, fine-tuning, the agent's verification rules and the build log.

### A. System architecture

SpatialScout separates thinking from computing: Meta models plan and verify, deterministic tools do the analysis, and every step is written to the audit log.

<img src="media/image2.png" style="width:6in;height:5.49107in" alt="SpatialScout system architecture · 5 layers" />

SpatialScout system architecture · 5 layers

The verifier (highlighted) sits beside the workers rather than after them, so no claim reaches the web app without being recomputed.

-   **Web app:** a web interface embedding the Vitessce viewer, the claims panel and voice input.

-   **Agents:** Muse Wonder and Muse Spark 1.3, called through the Meta Model API.

-   **Tools:** a Python MCP server; segmentation, SAM 3.1 inference and fine-tuning run as GPU jobs on Modal.

-   **Data:** an OME-Zarr spatial data store, the public reference data and the append-only audit log.

### B. Data sources and licences

Every dataset is public. GEO places no use restrictions of its own, but submitters can hold rights, so we cite each series and check its page before use.

| Dataset                                                                                                                               | Modality                                           | Groups                                                                                                      | Terms                                                            | Used for                                        |
|---------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------|-------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------|-------------------------------------------------|
| [GSE286184](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE286184), human glomerular disease                                   | Xenium, single-cell spatial                        | 3 control; 6 diabetic kidney disease; 4 IgA nephropathy; 4 minimal change disease; 5 membranous nephropathy | Public GEO; cite authors                                         | Segmentation audit; disease comparisons         |
| Same study, matched snRNA-seq ([summary](https://www.omicsdi.org/dataset/geo/GSE286184))                                              | Single-nucleus RNA-seq                             | 262,984 nuclei from 28 subjects, same disease groups                                                        | Public GEO; cite authors                                         | Reference for contamination metric              |
| [GSE333529](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE333529), human lupus nephritis                                      | Visium                                             | 4 lupus nephritis biopsies                                                                                  | Public GEO; cite authors                                         | Lupus nephritis case study                      |
| [GSE300895](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE300895), human nephrotic syndrome                                   | Visium HD                                          | Steroid-sensitive nephrotic syndrome, FSGS, relapsing nephrotic syndrome                                    | Public GEO; cite authors                                         | Audit on sequencing-based spatial data          |
| [GSE322686](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE322686), lupus mouse model                                          | Visium                                             | NZB/W F1 mice at 30 weeks, 4 replicates                                                                     | Public GEO; cite authors                                         | Disease-model case study                        |
| [10x Visium HD human kidney](https://www.10xgenomics.com/datasets/visium-hd-cytassist-gene-expression-libraries-human-kidney-ffpe-v4) | Visium HD with 20x H&E                             | 1 non-diseased donor                                                                                        | CC BY 4.0                                                        | Healthy reference; SAM 3.1 transfer test on H&E |
| HuBMAP Hacking the Kidney                                                                                                             | PAS whole-slide images with glomerulus annotations | Healthy kidney                                                                                              | **\[VERIFY licence on the HuBMAP Data Portal before training\]** | SAM 3.1 fine-tuning                             |
| [Stanley et al. 2020](https://www.nature.com/articles/s41467-020-15986-3)                                                             | Urine aptamer proteomics, &gt;1,100 proteins       | 7 active lupus nephritis, 8 inactive lupus, 8 healthy (screen)                                              | Open access; cite authors                                        | Urine-to-tissue mapping                         |
| [AMP RA/SLE](https://www.immport.org/resources/amp-ra-sle)                                                                            | Kidney immune-cell scRNA-seq; urine proteomics     | Lupus nephritis biopsies                                                                                    | ImmPort registration                                             | Immune-cell reference; positive controls        |

Sample groups for GEO series follow the [SpatialRenal catalogue](https://github.com/zqzneptune/SpatialRenal); confirm each against its GEO page before analysis.

### C. Segmentation methods and audit metrics

The audit runs several segmentations of the same tissue and scores every cell's purity against the matched single-nucleus reference.

**Segmentation conditions**

| Condition               | What it is                                                                                                                                                   |
|-------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 10x default             | Cell boundaries shipped with the Xenium or Space Ranger output                                                                                               |
| Proseg                  | Probabilistic segmentation driven by transcript positions                                                                                                    |
| Cellpose-SAM            | Image-based segmentation of nuclear and membrane stains                                                                                                      |
| 10x default + cellAdmix | Default boundaries, then removal of molecules assigned to the wrong cell ([cellAdmix](https://github.com/kharchenkolab/cellAdmix))                           |
| SpatialScout audit      | Best available cell boundaries, with SAM 3.1 tissue masks as hard limits: transcripts cannot belong to a cell across a glomerulus, tubule or vessel boundary |

**Metric 1: exclusive-marker contamination rate.** From the reference, choose marker pairs (g, h) that belong to different cell types and co-occur in fewer than 1% of nuclei; call this set P. The rate is the average, over pairs, of how often a cell expressing either marker expresses both:

C = \\frac{1}{\|P\|} \\sum\_{(g,h) \\in P} \\frac{\\\#\\{\\text{cells}: x\_g &gt; 0 \\land x\_h &gt; 0\\}}{\\\#\\{\\text{cells}: x\_g &gt; 0 \\lor x\_h &gt; 0\\}}

A perfectly segmented tissue scores close to the reference's own rate; contamination pushes C up.

**Metric 2: neighbour-marker load.** For each cell, the fraction of its transcripts that are markers of other cell types, compared with the reference expectation for its type.

**Metric 3: morphology–molecule agreement.** The log2 enrichment of podocyte markers inside versus outside predicted glomeruli (tubule markers for tubules), with a permutation p-value from shuffled masks.

**Labelling disease findings.** Each disease-versus-control finding gets one label. Default thresholds are below; we report results at each threshold we try.

1.  **Robust:** FDR &lt; 0.05 with the same direction in at least 3 of the 5 conditions.

2.  **Artifact:** significant under default segmentation, the gene is a marker of a neighbouring cell type (reference log2 fold change ≥ 1), and the effect shrinks by at least half or loses significance after the audit.

3.  **Newly revealed:** significant only after the audit, and not a marker of a neighbouring cell type.

### D. Statistical methods

The sample, not the cell, is the unit of replication; this one choice prevents most false disease findings in single-cell data.

-   **Pseudobulk.** Counts are summed per sample and cell type (or structure). Sample–type pairs with fewer than **\[20\]** cells are dropped.

-   **Test.** A negative binomial model (PyDESeq2) with disease status as the main term and study or sex as covariates where available. False discovery rate by Benjamini–Hochberg.

-   **Effect sizes.** Log2 fold changes with 95% confidence intervals, shrunk for low-count genes.

-   **Small samples.** With three controls, power is limited. Every finding reports its effect size, and a leave-one-sample-out analysis checks that no single biopsy drives it.

-   **Cross-study comparisons.** When diseased and control samples come from different studies, batch cannot be separated from disease. These comparisons are labelled exploratory; within-study comparisons are preferred.

-   **Spatial enrichment.** Marker enrichment inside tissue masks is tested against 1,000 random mask placements.

-   **Urine-to-tissue mapping.** Each urine protein is matched to its gene. Its source score is the share of tissue expression contributed by each cell type and structure, weighted by the disease fold change. Concordance between urine and tissue fold changes is a Spearman correlation across matched genes, tested against shuffled gene labels.

-   **Session-wide error control.** The verifier logs every test the agent runs in a session and applies FDR across all of them, so running many tests cannot manufacture a finding.

### E. Model fine-tuning

We fine-tune SAM 3.1 so that the prompt "glomerulus" reliably finds glomeruli. A 2026 preprint evaluating SAM 3 on pathology found that tiny, densely packed objects and specialised vocabulary fall outside its pretraining, and that text prompts alone are not enough ([arXiv 2604.18225](https://www.themoonlight.io/review/is-sam3-ready-for-pathology-segmentation)).

1.  **Data.** HuBMAP Hacking the Kidney PAS slides with expert glomerulus annotations **\[VERIFY licence and counts\]**. Splits are by slide, so no slide appears in both training and testing.

2.  **Tiling.** 1,024-pixel tiles at 20x; tiles without tissue are dropped.

3.  **Training.** SAM 3.1 weights (gated; request access on day one). Image and text encoders stay frozen; the detection head learns short concept phrases. Runs on Modal GPUs within the $100 credit: **\[TO MEASURE: GPU hours, cost\]**.

4.  **Evaluation.** Dice, IoU and detection F1 (IoU ≥ 0.5) on held-out slides, against stock SAM 3.1 with text and with box prompts.

5.  **Stain transfer.** The fine-tuned model is also scored on the H&E image of the 10x Visium HD kidney, against **\[PENDING: n\]** glomeruli annotated by hand and checked by a lab member.

6.  **Fallback.** If gated weights are not approved in time, SpatialScout uses SAM 3.1 through the Meta Model API with box prompts proposed by Muse Spark 1.3's vision, reported as its own condition.

**Stretch goal: an evidence-citing annotator.** A LoRA fine-tune of Meta's open-weights Muse Glimmer on Fireworks, trained to map marker genes to a cell-type label plus the marker evidence behind it. It is compared with the base model and Muse Spark 1.3 on held-out kidney cell types. Included only if the main pipeline ships first.

### F. Agent, verifier and audit trail

No claim reaches the scientist until a separate verifier has recomputed it and checked its plot.

**Tools.** Workers call analysis tools through an MCP server: load a dataset, run a segmentation method, score contamination, segment structures with SAM 3.1, map masks to cells, run a pseudobulk comparison, label findings, map urine proteins to tissue, test spatial enrichment, render a plot and search the literature.

**Claim format.** Every claim is structured data, so the verifier can check each field:

{  
"claim\_id": "c-0142",  
"text": "Gene X is higher in podocytes from disease than control",  
"statistic": "pseudobulk log2 fold change",  
"value": 1.8,  
"ci95": \[0.9, 2.7\],  
"fdr": 0.004,  
"n\_samples": {"disease": 6, "control": 3},  
"segmentation": "spatialscout\_audit",  
"label": "robust",  
"plot\_id": "p-0142",  
"dataset": "GSE286184",  
"code\_version": "git:abc1234"  
}

The values above are illustrative only.

**Verification checks**

1.  **Recompute.** The verifier reruns the statistic from raw counts through a separate code path. A mismatch beyond tolerance rejects the claim.

2.  **Plot check.** The rendered plot goes to Muse Spark 1.3 with structured questions, such as which group is higher. A plot that contradicts its claim is flagged.

3.  **Robustness.** A claim is called robust only if it holds under at least three segmentation conditions.

4.  **Provenance.** Every number links to its dataset, code version and parameters.

5.  **Planted errors.** The evaluation harness inserts known-false claims to measure how many the verifier catches.

**PI checkpoints.** The PI approves the plan, the segmentation choice and the final claims, by voice or click. Nothing is exported without approval.

**Audit trail.** Every action is an append-only log entry holding the prompt, tool, parameters, output hash, model and approver. Each entry includes the hash of the one before it, so any later edit to the history is detectable.

### G. Reproducibility and build log

Everything in this paper was built during the hackathon, October 27 to November 4, 2026, and reruns from the public repository.

-   **Repository:** **\[PENDING: public URL\]**, with dated commits from October 27.

-   **Run:** one command replays the cached demo analysis; a second reruns everything from raw data on Modal **\[CONFIRM commands\]**.

-   **Environment:** pinned Python dependencies and a container image.

-   **Replay:** any session can be replayed from its audit log, and any step re-executed.

| Component                                              | Origin                                              |
|--------------------------------------------------------|-----------------------------------------------------|
| Agent orchestration, verifier, claim format, audit log | Built during the hackathon                          |
| Segmentation audit metrics and finding labels          | Built during the hackathon                          |
| SAM 3.1 fine-tuning pipeline and evaluation            | Built during the hackathon                          |
| Urine-to-tissue mapping                                | Built during the hackathon                          |
| Viewer integration, claims panel, voice control        | Built during the hackathon, on open-source Vitessce |
| Proseg, Cellpose-SAM, cellAdmix, 2DE, Scanpy, PyDESeq2 | Third-party open-source tools, used as published    |
| Datasets                                               | Public, cited in Appendix B                         |

**Build log** (newest first; fill as milestones land)

| Date        | Milestone   |
|-------------|-------------|
| \[PENDING\] | \[PENDING\] |
| \[PENDING\] | \[PENDING\] |

### References

1.  Mitchel J, Gao T, Petukhov V, Cole E, Kharchenko PV. Impact and correction of segmentation errors in spatial transcriptomics. *Nature Genetics*, 2026. [Article](https://www.nature.com/articles/s41588-025-02497-4) · [summary](https://www.rna-seqblog.com/impact-and-correction-of-segmentation-errors-in-spatial-transcriptomics/) · [cellAdmix code](https://github.com/kharchenkolab/cellAdmix)

2.  Hanly JG, et al. The frequency and outcome of lupus nephritis: results from an international inception cohort study. *Rheumatology* 55(2):252–262, 2016. [Open access](https://escholarship.org/uc/item/5s98z3vv)

3.  Fava A, et al. Integration of urine proteomics and renal single-cell genomics identifies an interferon-gamma response gradient in lupus nephritis. *medRxiv*, 2020. [Preprint](https://www.medrxiv.org/content/10.1101/2020.03.13.20034348v1)

4.  Stanley S, et al. Comprehensive aptamer-based screening identifies a spectrum of urinary biomarkers of lupus nephritis across ethnicities. *Nature Communications*, 2020. [Article](https://www.nature.com/articles/s41467-020-15986-3) · [summary](https://mdedge.com/content/proteins-urine-may-predict-active-lupus-nephritis)

5.  Kong Q, et al. Is SAM3 ready for pathology segmentation? arXiv 2604.18225, 2026. [Review summary](https://www.themoonlight.io/review/is-sam3-ready-for-pathology-segmentation)

6.  2DE: a probabilistic method for differential expression across niches in spatial transcriptomics data. ICLR, 2025. [Paper page](https://iclr.cc/virtual/2025/35939)

7.  Single-nucleus transcriptomic landscape of human glomerular diseases \[Xenium\], GSE286184. [Dataset summary](https://www.omicsdi.org/dataset/geo/GSE286184)

8.  SpatialRenal: catalogue of public kidney spatial transcriptomics samples. [Repository](https://github.com/zqzneptune/SpatialRenal)

9.  10x Genomics. Visium HD Spatial Gene Expression Library, Human Kidney (FFPE). CC BY 4.0. [Dataset](https://www.10xgenomics.com/datasets/visium-hd-cytassist-gene-expression-libraries-human-kidney-ffpe-v4)

10. Accelerating Medicines Partnership RA/SLE data. [ImmPort resource](https://www.immport.org/resources/amp-ra-sle)

11. Meta. Model pages for [SAM 3.1](https://dev.meta.ai/models/sam-3-1), [Muse Spark 1.3](https://dev.meta.ai/models/muse-spark) and [Muse Wonder](https://dev.meta.ai/models/muse-wonder).
