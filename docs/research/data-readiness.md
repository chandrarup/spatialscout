# Data readiness: GSE286184 (Xenium, human glomerular disease)

Probed Nov 2 2026 by downloading one control section's files and the paper's supplement. The background agent stalled while parsing GEO's SOFT metadata, so these facts were checked directly.

Sources:
- [geo-series]: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE286184
- [geo-files]: https://ftp.ncbi.nlm.nih.gov/geo/series/GSE286nnn/GSE286184/suppl/ (file listing, sizes)
- [geo-samples]: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE286184&targ=gsm&form=text&view=brief
- [paper-supp]: supplementary methods (mmc2.pdf) of https://pmc.ncbi.nlm.nih.gov/articles/PMC13586693/ , section "Xenium in situ profiling and generation" and "Xenium In Situ analysis"
- [snrna-files]: https://ftp.ncbi.nlm.nih.gov/geo/series/GSE271nnn/GSE271188/suppl/ (matched single-nucleus reference)

## Verdicts

| Question | Verdict | Evidence |
| --- | --- | --- |
| Transcript table with x, y, gene, assigned `cell_id` | **YES**, every section | `GSM*_transcripts.parquet.gz` per sample [geo-files] |
| `overlaps_nucleus` flag | **YES** | Column present; ~50/50 split in the control section probed |
| `nucleus_distance` per transcript | **YES** | Column present (µm) |
| Quality score | **YES** | `qv`; median 40, 90% ≥ 20 |
| Cells table | **YES** | `cell_id, x_centroid, y_centroid, transcript_counts, control_probe_counts, ..., total_counts, cell_area, nucleus_area` |
| Cell boundary polygons | **NO** | Not deposited [geo-files] |
| Nucleus boundary polygons | **NO** | Not deposited [geo-files] |
| Morphology (DAPI) or H&E images | **NO** | Not deposited, though the paper took post-run H&E [paper-supp] |
| Cell-type labels per Xenium cell | **NO** | Authors annotated in Seurat by markers but did not deposit labels [paper-supp] |
| Panel | **50 genes** | `features.tsv` (541 features incl. controls) |
| Whole-series download size | **335 MB** | `GSE286184_RAW.tar` = 335,585,280 bytes [geo-files] |
| Single-nucleus reference | **YES**, GSE271188 | `GSE271188_RAW.tar` = 3.1 GB; per-sample `matrix.mtx.gz` 23–118 MB [snrna-files] |

## Segmentation used by the authors

"Imaging processing, cell segmentation, image registration, decoding, deduplication, and secondary analysis were conducted using the Xenium Onboard Analysis pipeline v.3.1.0". "Glomeruli were segmented using the onboard analysis software (Xenium Explorer, version 2.0), which applies nuclear expansion–based segmentation" [paper-supp]. Nuclear-expansion segmentation assigns cytoplasmic transcripts by proximity, which is the regime where Mitchel et al. (2026) show neighbour admixture distorts differential expression.

## A published finding worth auditing

The authors write: "Cells initially annotated as podocytes that co-expressed LRP2 and CUBN were reclassified as 'Podocyte endocytosis', whereas cells co-expressing ALDH1A2 and NPHS1 were annotated as 'Intermeditae cell'" [paper-supp]. LRP2 and CUBN are proximal-tubule markers. Whether that co-expression survives nucleus-restricted assignment is exactly the question SpatialScout is built to ask. Either answer is informative, and it is a real, citable question rather than a scripted one.

## Samples

Group labels from GEO `condition:` [geo-samples]. Each GEO sample is one Xenium section.

| Group | Sections (GEO) | Patients (paper) | GSM / section name |
| --- | --- | --- | --- |
| Control | 3 | 3 | GSM8720409 x1, GSM8720410 x2, GSM8720414 x6 |
| DKD | 6 | 5 | GSM8720411 x3, GSM8720412 x4, GSM8720413 x5, GSM8720415 x7, GSM8720416 x8, GSM8720417 x9 |
| IgAN | 4 | 4 | GSM8720418 x10, GSM8720419 x11, GSM8720420 x12, GSM8720421 x13 |
| MCD | 4 | 3 | GSM8720422 x14 – GSM8720425 x17 |
| MN | 5 | 4 | GSM8720426 x18 – GSM8720430 x22 |

**Risk: 22 sections from 19 patients.** The paper says "The dataset consisted of 19 patient samples, comprising Control (n = 3), DKD (n = 5), MN (n = 4), MCD (n = 3), and IgAN (n = 4)" [paper-supp]. GEO does not say which sections share a patient. DKD, MCD and MN each contain one extra section from a repeat patient. Treating sections as independent donors would pseudo-replicate. Control (3 sections, 3 patients) is clean. Mitigations: infer likely same-patient pairs (similar tissue extent and gene composition), report leave-one-section-out stability, and disclose the limitation in the capability report.

## Panel coverage (control section x2)

All 50 genes: ALDH1A2, AQP2, C3, CALCR, CD38, CD3D, CD4, CD68, CD8A, CLCN5, COL1A1, CUBN, DHFR, ETS1, FCGR3A, FKBP5, FN1, FOLR1, HLA-DRA, IL10RA, IL18, ISG20, ITGAX, JUN, KLF9, LAMC2, LRP2, MKI67, MS4A1, NPHS1, PARL, PDGFRB, PECAM1, POSTN, PTH2R, PTPRC, RHEX, SELENOT, SLC12A3, SLC4A1, SREBF1, STAT1, TGFB1, TNFAIP1, TNFAIP2, TNFSF10, UMOD, VCAM1, ZBTB16, ZFP36.

| Compartment | Present | Absent (from the PRD's wish list) |
| --- | --- | --- |
| Podocyte | NPHS1 | NPHS2, PODXL, WT1, PTPRO |
| Parietal epithelium | ALDH1A2 | |
| Proximal tubule | LRP2, CUBN, CLCN5 | SLC34A1, HAVCR1 |
| Loop / distal / collecting duct | UMOD, SLC12A3, AQP2, SLC4A1, CALCR | SLC12A1 |
| Endothelium / mesangium | PECAM1, PDGFRB | EMCN, PLVAP, KDR, ACTA2 |
| T / B / plasma cells | CD3D, CD4, CD8A, PTPRC, MS4A1, CD38 | CD3E |
| Myeloid | CD68, ITGAX, FCGR3A, HLA-DRA | CD163, C1QA |
| Injury, fibrosis, interferon | VCAM1, POSTN, COL1A1, FN1, TGFB1, STAT1, ISG20, IL18, TNFSF10, MKI67 | CXCL9, CXCL10, LCN2 |
| Urine-biomarker genes (Stanley 2020) | VCAM1 | ALCAM, PF4, TFPI, VSIG4 |

Implications:
- The urine bridge shrinks to the panel genes that encode a Stanley 2020 urine protein. VCAM1 is confirmed; the rest need a check of Stanley's full table against the 50-gene panel before that module is scoped.
- Exclusive marker pairs for the co-expression proxy exist in-panel, for example (NPHS1, CD3D), (NPHS1, LRP2), (UMOD, LRP2), (AQP2, UMOD), (CD3D, CD68), (MS4A1, CD68). Freeze them from the single-nucleus reference or a development section before evaluation.

## Shape of one section (control x2, GSM8720410)

- 313,158 transcripts, 17,935 cells, 17.0% of transcripts unassigned, 3.0% control probes.
- Tissue extent about 3,000 × 13,700 µm.
- Most abundant genes: UMOD 51.6k, ZFP36 42.8k, AQP2 24.9k, SLC12A3 22.3k, JUN 22.0k, CUBN 15.3k.
- Whole cohort fits in memory on a laptop; the batch audit is CPU work, not GPU work.

## What this means for the build

- The core audit is feasible on the real cohort: compare **default** assignment (`cell_id`), **nucleus-only** (`overlaps_nucleus == 1`), and a **distance cap** (`nucleus_distance` threshold) with no extra inputs.
- Cell types must be annotated by us from panel markers, labelled as our annotation.
- There are no images, so SAM 3.1 needs an image we derive from the transcripts (a rendered RNA-density image of the section) or the separate 10x kidney preview dataset (not probed here). Markers used to render or prompt a mask must not also be used to validate that mask.
- Display cell outlines are approximations (nucleus area → circle, or a hull of nuclear transcripts) and must be labelled as such.
