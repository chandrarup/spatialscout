# Agent Directive: Re-Centering SpatialScout on the Interactive Dual-Biopsy TIFF & Hypothesis-Testing Demo

> **CRITICAL COURSE CORRECTION FOR CODING AGENTS:** Read this directive immediately before proceeding with `docs/spec/spec.md` and `docs/spec/tickets-draft.md`. Earlier agent revisions stripped out real microscopy `.tif` images because `GSE286184` only deposited `(x, y)` tables, reducing the product to an abstract scatter-plot CSV filter. **That is NOT the product vision and will not win the 25% Demo or 30% Impact scores at the [Meta Global AI Developer Hackathon](https://cerebralvalley.ai/e/meta-ai-developer-hackathon).**
>
> Below is the exact **Interactive Dual-Biopsy TIFF + Region-Selection + Hypothesis Verdict** workflow that must drive the UI and demo, grounded in real open-access kidney `.tif + .csv` spatial datasets from **HuBMAP**, **KPMP**, and **GSE286184**, while preserving 100% of our `ADR-0001` scientific integrity guardrails.

## 1. The Core Demo Experience (What the User & Judges Actually Do on Screen)

Instead of opening a static table of pre-computed section numbers, the application is an **Interactive Dual-Biopsy Spatial Microscope & Hypothesis Tester** (inspired by the [Akoya PhenoCycler Web Viewer](https://dataset.akoyabio.com/#s=0#w=0#g=0#m=-1#a=-100_-100#v=0.5_0.3277_0.5#o=-100_-100_1_1#p=Q) and [Pachter Lab Voyager CODEX workflows](https://pachterlab.github.io/voyager/articles/codex_landing.html)):

1. **Step 1 — Open Two Real Kidney Biopsy `.tif` Images Side-by-Side (Healthy Control vs. Diseased Patient):**
   * **Left Viewport:** Healthy Reference Kidney Biopsy multi-channel fluorescence `.tif` (DAPI nuclei in blue, Podocyte/Glomerular markers `NPHS1`/`PODXL` in cyan, Tubule markers `LRP2`/`UMOD` in green, Immune/Fibrosis markers `CD8`/`CD3`/`POSTN` in magenta).
   * **Right Viewport:** Diseased Patient Kidney Biopsy `.tif` (CKD / DKD patient biopsy with clinical metadata badge: e.g., `eGFR`, `Proteinuria`, `KDIGO Stage` from [KPMP Kidney Tissue Atlas](https://atlas.kpmp.org/repository/)).
2. **Step 2 — Draw/Select Regions of Interest (ROIs) on Both Biopsies & Ask an Intuition/Hypothesis Question:**
   * The researcher drags a bounding box (or clicks **"Auto-Match Glomerular ROIs"**) to select a glomerulus + periglomerular neighborhood on the **Healthy Control `.tif`** and a corresponding region on the **Diseased Patient `.tif`**.
   * The researcher speaks (`Muse Voice Transcribe`) or types their intuition:
     > *"My hypothesis is that in this diseased patient's biopsy compared to healthy control, infiltrating immune cells and POSTN+ myofibroblasts are invading the glomerulus and driving podocyte endocytosis/injury—and that UMOD expression in B-cells is also elevated. Segment these two selected regions, clean up boundary spill-over, and prove whether my intuition is right or wrong."*
3. **Step 3 — Live `SAM 3.1` Segmentation on the Selected `.tif` Regions + Cell Boundary De-Contamination:**
   * `Muse Wonder` creates the execution plan for the two selected ROIs.
   * `SAM 3.1` runs directly on the selected `.tif` image crops (plus the underlying single-cell `.csv` / `.parquet` coordinates), outlining the glomeruli, tubules, and cell boundaries in crisp cyan.
   * The **Boundary De-Contamination Engine** compares **Standard/Default Cell Assignment** (which suffers from lateral membrane/cytoplasmic bleed across crowded cells, per [Mitchel et al. 2026](https://www.rna-seqblog.com/impact-and-correction-of-segmentation-errors-in-spatial-transcriptomics/)) against **De-Contaminated Assignment** (clipping lateral spill-over against `SAM 3.1` structural masks and nuclear cores, controlled against our closed-form random-thinning expectation). Excluded spill-over signals light up in bright yellow right on the `.tif` overlay.
4. **Step 4 — Downstream Analysis & "Hypothesis Verdict" (Proving Intuition Right vs. Wrong for Precision Research):**
   * The engine runs downstream comparative analysis between the **Healthy ROI** and **Diseased Patient ROI** (cell-type composition shift, spatial neighborhood colocalization / Moran's $I$ / Lee's $L$ per [Voyager](https://pachterlab.github.io/voyager/articles/codex_landing.html), and marker fold-change before vs. after de-contamination).
   * `Muse Spark Open` (on **Baseten**) drafts the comparative findings and `Muse Spark 1.3` (Vision Verifier) checks both the statistical plots and the `.tif` ROI crops to issue two crystal-clear verdicts:
     * **VERDICT 1 — INTUITION CONFIRMED (True Patient Biology):** Podocyte `LRP2`/`CUBN` endocytosis state and periglomerular immune/myofibroblast infiltration are genuinely elevated in the Diseased Patient ROI vs. Healthy Control, surviving strict nuclear and `SAM 3.1` boundary de-contamination.
     * **VERDICT 2 — INTUITION REFUTED (Segmentation Spill-Over Illusion):** The apparent `UMOD` elevation inside B-cells in the Diseased Patient ROI **collapses by >75% after boundary de-contamination**—proving it was false lateral spill-over from neighboring thick ascending limb tubules, saving the researcher from chasing a false target!
   * **Patient-Level Translational Summary Card:** Displays the patient's verified molecular profile alongside non-invasive urine biomarker correlates (`VCAM-1` / `ALCAM` from [Stanley et al. 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7198599/)) and pathway candidates from [PMC13586693](https://pmc.ncbi.nlm.nih.gov/articles/PMC13586693/) (strictly badged *"For Research Hypothesis Generation Only — Not Clinical Advice"*).

## 2. Real Public `.tif + .csv` Kidney Datasets to Power the Dual-Biopsy Viewer

To make the `.tif` microscopy viewer and the single-cell math 100% real and fast to load (without downloading 50 GB zip files in the browser), pre-extract **high-resolution 2,048×2,048 multi-channel `.tif` (converted to fast WebP/PNG channel layers + raw TIFF download) and matched single-cell `.csv`/`.parquet` tables** from these verified sources:

| Dataset Source | What It Provides | Role in the Dual-Biopsy Demo |
| :--- | :--- | :--- |
| **[HuBMAP Kidney PhenoCycler (`32f9aca44de5f66fbe950bce7da75536`)](https://portal.hubmapconsortium.org/browse/dataset/32f9aca44de5f66fbe950bce7da75536)** & **[HuBMAP DeepCell + SPRM Search](https://www.google.com/search?q=https://portal.hubmapconsortium.org/search/datasets%3Forgan%3DKidney%2B%28Right%29%26dataset_type%3DPhenoCycler.PhenoCycler,PhenoCycler.PhenoCycler%2B%5BDeepCell%2B%252B%2BSPRM%5D)** | Real multiplex fluorescence `.ome.tif` kidney images + `DeepCell` cell/nucleus segmentation masks + `SPRM` cell-by-marker spatial quantification CSVs. | Provides real human kidney `.tif` fluorescence channels + pre-computed nuclear vs. whole-cell masks so `SAM 3.1` can segment real microscopy tissue directly. |
| **[KPMP Kidney Tissue Atlas (`CODEX tif + csv`)](https://atlas.kpmp.org/repository/?size=n_1000_n&filters%5B0%5D%5Bfield%5D=protocol&filters%5B0%5D%5Bvalues%5D%5B0%5D=KPMP%20Main%20Protocol&filters%5B0%5D%5Btype%5D=any&filters%5B1%5D%5Bfield%5D=experimental_strategy&filters%5B1%5D%5Bvalues%5D%5B0%5D=CODEX&filters%5B1%5D%5Btype%5D=any&filters%5B2%5D%5Bfield%5D=data_type&filters%5B2%5D%5Bvalues%5D%5B0%5D=Imaging&filters%5B2%5D%5Btype%5D=any&filters%5B3%5D%5Bfield%5D=data_format&filters%5B3%5D%5Bvalues%5D%5B0%5D=tif%20csv&filters%5B3%5D%5Btype%5D=any&sort%5B0%5D%5Bfield%5D=file_size&sort%5B0%5D%5Bdirection%5D=desc)** | Paired **Healthy Reference** (`164-17`) and **CKD / AKI Diseased Patient** (`31-10013`, `29-10394`, `30-11141`) CODEX `image_collection.zip` (`tif + csv`) with clinical metadata (`eGFR`, `Proteinuria`, `KDIGO Stage`). | Enables the **Side-by-Side Healthy Control vs. Diseased Patient Biopsy** comparison with real clinical context per patient biopsy. |
| **[GSE286184 Human Glomerular Disease Xenium Atlas](https://pmc.ncbi.nlm.nih.gov/articles/PMC13586693/)** | Sub-cellular `(x, y)` transcript coordinates across 22 human biopsies (Control, DKD, IgAN, MCD, MN) with nuclear vs. expansion-zone assignment flags (`overlaps_nucleus`). | Powers our sub-cellular transcript de-contamination math (`LRP2`/`CUBN` in podocytes vs. `UMOD` spill-over in B-cells) and multi-section statistical validation. |

> **Fast Data Architecture Tip for Agent 1:** Do NOT force the web app to parse a 4 GB raw `.zip` at runtime. In Ticket 02, write a preprocessing script that extracts **2 matched Healthy vs. Diseased 2,048×2,048 multi-channel TIFF fields-of-view** (rendered as toggleable fluorescence channel layers + composite TIFF) alongside their exact single-cell/molecule tables in Parquet, and keep the cohort-wide 22-section [GSE286184](https://pmc.ncbi.nlm.nih.gov/articles/PMC13586693/) tables as the statistical backing store that proves whether the single-biopsy ROI observation holds across the cohort!

## 3. How to Update the Tickets (`tickets-draft.md`) to Build This Without Breaking Deadlines

Instead of throwing away the solid backend architecture you already designed in Tickets 01–12, **upgrade the UI, Viewer, and Agent Workflow in Tickets 02, 05, 07, 09, and 10** so they deliver this exact Side-by-Side Dual-Biopsy ROI experience:

### 3.1 Ticket 02 & Ticket 05: Side-by-Side Dual-Biopsy TIFF Viewer + Interactive ROI Box Selection

* **Dual-Biopsy Viewports (`Healthy Biopsy` on Left vs. `Diseased Patient Biopsy` on Right):**
  * Render actual multi-channel fluorescence microscopy imagery (`.tif` channel layers: `DAPI / Nuclei`, `Glomerulus / Podocyte`, `Proximal / Distal Tubule`, `Immune Infiltrate`) underneath the `deck.gl` cell/molecule vector overlay, matching the visual polish of the [Akoya PhenoCycler viewer](https://dataset.akoyabio.com/#s=0#w=0#g=0#m=-1#a=-100_-100#v=0.5_0.3277_0.5#o=-100_-100_1_1#p=Q).
* **Interactive Region-of-Interest (ROI) Selection Tool:**
  * Allow the researcher to **drag a rectangle (`selected_roi_healthy`, `selected_roi_diseased`)** on both biopsies—or click a **"Snap to Glomerular ROIs"** button—and pass those exact `(x_min, y_min, x_max, y_max)` coordinates as parameters into the `POST /api/investigations` request!
  * All downstream tools (`run_sam_segmentation`, `audit_roi_assignment`, `compare_healthy_vs_diseased_roi`, `check_cohort_consistency`) execute on the **user-selected regions first**, then check whether that patient-level finding holds across the broader cohort.

### 3.2 Ticket 07: `SAM 3.1` Segments the User-Selected `.tif` Biopsy Region Live

* Because the viewer now displays real fluorescence `.tif` microscopy crops inside the user's selected ROI box, `SAM 3.1` runs **directly on the selected biopsy image region** (seeded by glomerular/tubular marker clusters or user box drag) to produce crisp anatomical segmentation masks (`Glomerular Tuft`, `Periglomerular Immune Ring`, `Adjacent Tubules`).
* Any molecule or fluorescence signal assigned to a cell inside the glomerulus whose coordinate actually sits across the `SAM 3.1` boundary in an adjacent tubule or immune aggregate is highlighted in **bright yellow as Boundary Spill-Over**.

### 3.3 Ticket 06 & Ticket 09: The 3-Step Scientific Story ("Intuition -> De-Contaminated Segmentation -> Verdict")

Structure the Agent Orchestrator (`Muse Wonder` + `Muse Spark 1.3` + Baseten `Muse Spark Open`) around the exact workflow a translational researcher cares about:

1. **Step 1 — State the Clinical/Research Hypothesis on the Selected Biopsy Pair:**
   * Researcher selects the Healthy vs. Diseased Patient ROIs and asks a hypothesis question (by voice via `Muse Voice Transcribe` or text).
   * `Muse Wonder` translates the intuition into concrete testable sub-hypotheses on the selected regions.
2. **Step 2 — Segment & De-Contaminate the Selected Regions (`SAM 3.1` + Assignment Audit + Thinning Control):**
   * The agent segments the selected regions, strips out boundary spill-over (`default` vs. `nucleus_only` / `distance_cap` / `SAM 3.1 structure_constrained`), and runs the **closed-form random-thinning control** ($C_{\text{thin}} - C_{\text{observed}}$) and **label-sensitivity check** autonomously via `Muse Spark 1.3` follow-up tool calls.
3. **Step 3 — Downstream Analysis & Intuition Verdict (`CONFIRMED` vs. `REFUTED: ARTIFACT`):**
   * Computes downstream spatial metrics on the cleaned cells (Healthy ROI vs. Diseased Patient ROI marker expression, cell-type enrichment, and spatial colocalization per [Voyager](https://pachterlab.github.io/voyager/articles/codex_landing.html), backed by [GSE286184](https://pmc.ncbi.nlm.nih.gov/articles/PMC13586693/) cohort replication).
   * Renders a prominent **Hypothesis Verdict Banner** at the top of the results panel:
     * **CONFIRMED BY AUDIT:** Shows which part of the researcher's intuition survived strict segmentation and boundary cleaning (e.g., podocyte injury / `LRP2`/`CUBN` endocytosis and periglomerular immune/fibroblast infiltration in the patient biopsy).
     * **REFUTED (SEGMENTATION ARTIFACT):** Shows which part of the initial raw signal was actually a false positive caused by neighbor spill-over (e.g., tubular `UMOD` bleeding into adjacent B-cells), demonstrating why naive analysis without SpatialScout leads precision medicine astray!

### 3.4 Ticket 10: Dual-Biopsy Visual Verification + Interactive "Challenge Verifier" Toggle

* Pass the rendered **Healthy vs. Diseased ROI comparison figure** (showing both the `.tif` segmentation crop with yellow spill-over molecules and the quantitative comparison chart) to `Muse Spark 1.3` vision to verify that the text claim matches the visual biopsy evidence.
* Keep the interactive **"Challenge Verifier: Inject Error"** selector on the Claim Card so judges can test the verifier live in Replay Mode.