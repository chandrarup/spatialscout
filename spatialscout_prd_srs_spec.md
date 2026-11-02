# SpatialScout: Product Requirements Document (PRD), Software Requirements Specification (SRS) & Multi-Agent Parallel Build Spec

**Target Event:** [Meta Global AI Developer Hackathon](https://cerebralvalley.ai/e/meta-ai-developer-hackathon) ($1,000,000 Prize Pool)  
**Submission Deadline:** November 4, 2026, 9:00 PM ET (November 5, 2026, 02:00 UTC) via the [Cerebral Valley Submission Portal](https://cerebralvalley.ai/e/meta-ai-developer-hackathon/hackathon/submit)  
**Recommended Track:** Indie Developer Track ($150,000 1st Prize — judged on creativity, technical ambition, and working demo)  
**Primary Themes:** *Push the Frontier* (Accelerating Scientific Discovery) & *Build for Your World* (Translational Pathology)  
**Compute & Inference Stack ($375 Total Hackathon Credits):** [Meta Model API](https://dev.meta.ai/events/global-hackathon) ($150) + **Modal** ($100 Serverless GPUs) + **Baseten** ($100, 2M TPM Open-Weights Inference) + **Fireworks AI** ($25 Open-Weights LoRA Fine-Tuning)

## 1. Executive Summary & Winning Business Objectives (BRD)

SpatialScout is an agentic spatial biology auditing platform built on the [Meta Developer Platform](https://dev.meta.ai/events/global-hackathon) (`Muse Wonder`, `Muse Spark 1.3`, `SAM 3.1`, `Muse Voice Transcribe`, `Muse Code`) and Meta's open-weights models (`Muse Spark Open` on **Baseten**, `Muse Glimmer` LoRA on **Fireworks**, and `SAM 3.1` GPU fine-tuning on **Modal**). It solves a critical failure mode identified in recent spatial transcriptomics research ([Mitchel et al. 2026](https://www.rna-seqblog.com/impact-and-correction-of-segmentation-errors-in-spatial-transcriptomics/)): when immune cells infiltrate diseased kidney tissue, standard cell segmentation boundaries leak, causing neighboring RNA molecules to be misassigned and creating false "disease signatures."

Every feature in this specification is reverse-engineered from the four official [hackathon judging weights](https://reconscribe.com/meta-global-ai-developer-hackathon-2026/) to maximize scoring efficiency before the November 4 cutoff:

| Judging Criterion | Weight | Product Requirement That Captures Full Marks | Acceptance Metric |
| :--- | :--- | :--- | :--- |
| **Impact** | **30%** | Eliminates false kidney drug targets in human glomerular disease ([GSE286184](https://pmc.ncbi.nlm.nih.gov/articles/PMC13586693/)) and lupus nephritis ([GSE322686](https://pmc.ncbi.nlm.nih.gov/articles/PMC13338671/)), linking surviving genes to non-invasive urine biomarkers ([Stanley et al. 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7198599/)). | Identifies >=30% of top default differential expression hits as segmentation leakage artifacts and maps surviving hits to validated urinary proteins (`VCAM1`, `ALCAM`). |
| **Use of Meta AI Tooling** | **25%** | Unites **Hosted Meta API** (`Muse Wonder`, `Muse Spark 1.3`, `SAM 3.1` video-tile stitching, `Muse Voice Transcribe`) with **Meta Open-Weights** (`Muse Spark Open` at 2M TPM on Baseten + LoRA-tuned `Muse Glimmer` on Fireworks + `SAM 3.1` fine-tuning on Modal GPUs). | Showcases 7 Meta models/tools across all 3 official hackathon inference partners (Modal, Baseten, Fireworks) with zero non-Meta models. |
| **Demo** | **25%** | Delivers a 60fps split-screen interactive spatial viewer ("Standard 10x Pipeline" vs. "SpatialScout Audited Pipeline") where leaked RNA molecules light up in yellow and fake disease targets vanish on click or voice command. | Complete 4-beat "Golden Path" demo runs end-to-end in <90 seconds with zero page reloads and instant deterministic replay fallback. |
| **Technical Depth & Execution** | **20%** | Enforces sample-level pseudobulk statistics (`PyDESeq2`/`scipy`) on Modal sandboxes, deterministic verification recompute, and a SHA-256 hash-chained audit trail exported as a reproducible notebook. | 100% of agent claims pass schema validation, independent recomputation within `1e-4` tolerance, and `Muse Spark 1.3` visual plot inspection. |

## 2. How Modal, Baseten & Fireworks Supercharge the Architecture

Integrating all three official hackathon partner platforms listed on the [Meta Global AI Developer Hackathon page](https://cerebralvalley.ai/e/meta-ai-developer-hackathon) gives SpatialScout a massive technical and judging edge while protecting your $150 hosted [Meta Model API](https://dev.meta.ai/events/global-hackathon) credits:

| Partner Platform & Credit | Meta Model / Workload Hosted | Exact Role in SpatialScout | Why Judges & Sponsors Love It |
| :--- | :--- | :--- | :--- |
| **[Meta Model API](https://dev.meta.ai/events/global-hackathon) ($150)** | `Muse Wonder`, `Muse Spark 1.3` (Vision Verifier), `SAM 3.1` (Video Tracking API), `Muse Voice Transcribe` | Orchestrates the top-level DAG plan, runs multimodal visual verification on rendered plots, tracks glomeruli across slide tile seams, and handles live voice commands. | Uses every flagship hosted capability in `https://api.meta.ai/v1`. |
| **Modal ($100 Credits)** | `SAM 3.1` Pathology Fine-Tuning (`A100`/`H100`) + Parallel Spatial Math Sandbox | Runs the [HuBMAP Hacking the Kidney](https://www.kaggle.com/competitions/hubmap-kidney-segmentation) `SAM 3.1` head fine-tune and executes parallel `Shapely`/`PyDESeq2` batch audits across all 22 [GSE286184](https://pmc.ncbi.nlm.nih.gov/articles/PMC13586693/) biopsies in <30 seconds. | Offloads heavy spatial polygon clipping and GPU training from your laptop to serverless GPUs. |
| **Baseten ($100 Credits + 2M TPM)** | `Muse Spark Open` (Meta Open-Weights) | Powers the high-throughput worker swarm that scores candidate gene claims and literature provenance across dozens of cell types concurrently at 2,000,000 tokens/min. | Preserves your $150 hosted Meta API credits for vision/planning while making multi-gene worker sweeps instantaneous. |
| **Fireworks AI ($25 Credits)** | `Muse Glimmer` (Meta Open-Weights + LoRA Fine-Tune) | Runs a lightweight LoRA fine-tuned **Evidence-Citing Cell Annotator** trained on [GSE286184](https://pmc.ncbi.nlm.nih.gov/articles/PMC13586693/) single-nucleus reference markers (`NPHS1` -> Podocyte, `CD3D` -> T-cell) to score cell purity. | Directly implements your whitepaper's Appendix E stretch goal and showcases open-weights fine-tuning from the Fireworks hackathon workshop. |

## 3. Monorepo Directory Contract

To allow four coding agents (or sub-agents in `Muse Code`) to build the stack simultaneously with **zero merge conflicts**, the repository is partitioned into strict module boundaries that communicate only through immutable JSON/Pydantic/TypeScript schemas in `/contracts`.

```text
spatialscout/
├── contracts/                      # READ-ONLY shared schemas (locked first)
│   ├── schemas.json                # JSON Schema for ROI, Claim, AuditEntry, PlanDAG
│   ├── models.py                   # Pydantic v2 models imported by all Python modules
│   └── types.ts                    # TypeScript interfaces imported by Frontend
├── data_engine/                    # WORKSTREAM 1 (Agent 1: Data, Spatial Math & Modal GPU Jobs)
│   ├── modal_app.py                # Modal serverless GPU functions (SAM 3.1 fine-tune & batch audit)
│   ├── scripts/
│   │   ├── extract_hero_rois.py    # Extracts 3 ROIs from GSE286184 + Stanley 2020 CSV
│   │   └── run_batch_benchmarks.py # Generates whitepaper Tables 1-3 metrics via Modal
│   ├── spatial_math.py             # Exclusive-marker contamination C & Shapely clipping
│   ├── stats_engine.py             # Pseudobulk DE, planted outlier generator, plot renderer
│   └── fixtures/                   # Pre-computed fast-load JSON/Parquet for instant demo
├── meta_models/                    # WORKSTREAM 2 (Agent 2: Meta API, Baseten, Fireworks & SAM 3.1)
│   ├── client.py                   # Unified router: Meta API + Baseten (Spark Open) + Fireworks (Glimmer)
│   ├── sam_video_stitcher.py       # Streams 4x4 slide tiles as MP4 frames to SAM 3.1 (API or Modal GPU)
│   ├── glimmer_lora_annotator.py   # Fireworks LoRA fine-tune & inference for Muse Glimmer cell typing
│   ├── spark_vision_verifier.py    # Sends Matplotlib PNG + Claim JSON to Muse Spark 1.3
│   └── voice_transcriber.py        # Muse Voice Transcribe speech-to-text endpoint
├── agent_server/                   # WORKSTREAM 3 (Agent 3: Orchestrator, MCP & Audit Log)
│   ├── main.py                     # FastAPI server + SSE streaming + Replay Mode
│   ├── wonder_planner.py           # Muse Wonder 4-step DAG planner
│   ├── spark_worker.py             # Parallel worker loop (Baseten Muse Spark Open + Meta Spark 1.3)
│   ├── mcp_tools.py                # Deterministic tool registry calling data_engine & Modal
│   └── audit_chain.py              # Append-only SHA-256 hash-chained provenance logger
└── web_ui/                         # WORKSTREAM 4 (Agent 4: Split-Screen React UI)
    ├── src/
    │   ├── components/
    │   │   ├── VoiceCommandBar.tsx # Mic recorder + Live Partner Badge (Meta + Modal + Baseten + Fireworks)
    │   │   ├── SplitViewer.tsx     # HTML5 Canvas/Deck.gl: Default vs. SAM 3.1 Audited ROI
    │   │   ├── ClaimsVerifier.tsx  # Claims drawer + Spark 1.3 Vision "Caught Lie" modal
    │   │   └── UrineOmicsMap.tsx   # Tissue-to-urine biomarker chord/sankey link card
    │   └── state/
    │       └── demoStore.ts        # Live SSE state + 1-click "Offline Verified Replay"
```

## 4. Shared Data Contracts (`/contracts`) — Lock Before Parallel Work

All parallel agents must code against these three canonical payloads. Do not modify field names once parallel execution begins.

### 4.1 `SpatialROI` Payload (`GET /api/roi/{roi_id}`)

```json
{
  "roi_id": "gse286184_dkd_glom_01",
  "dataset": "GSE286184",
  "disease_group": "Diabetic Kidney Disease",
  "dimensions_px": [2048, 2048],
  "tile_grid": { "rows": 4, "cols": 4, "tile_size_px": 512 },
  "sam31_glomerulus_polygons": [
    [[412.0, 510.5], [489.2, 502.1], [540.8, 580.0], [412.0, 510.5]]
  ],
  "cells": [
    {
      "cell_id": "c_8821",
      "cell_type": "Podocyte",
      "glimmer_annotated_type": "Podocyte (NPHS1+, NPHS2+, CD3D-)",
      "centroid": [455.2, 540.1],
      "default_polygon": [[440, 520], [475, 520], [475, 565], [440, 565]],
      "audited_polygon": [[440, 520], [462, 520], [462, 555], [440, 555]],
      "contamination_score_default": 0.42,
      "contamination_score_audited": 0.04
    }
  ],
  "transcripts": [
    {
      "mol_id": "t_99102",
      "gene": "CD3D",
      "x": 469.5,
      "y": 548.0,
      "default_cell_id": "c_8821",
      "audited_cell_id": "c_8822_tcell",
      "is_boundary_leak": true,
      "leak_reason": "Crosses SAM 3.1 glomerular basement membrane mask from adjacent CD3+ T-cell"
    }
  ]
}
```

### 4.2 `VerifiedClaim` Payload (`POST /api/analyze` SSE Stream & Final Response)

```json
{
  "claim_id": "c-0142",
  "gene": "VCAM1",
  "cell_type": "Podocyte",
  "text": "VCAM1 is upregulated in diseased podocytes and survives SAM 3.1 boundary auditing",
  "statistic": "pseudobulk_log2fc",
  "default_log2fc": 2.41,
  "audited_log2fc": 2.18,
  "ci95": [1.45, 2.91],
  "fdr": 0.0018,
  "n_samples": { "disease": 6, "control": 3 },
  "label": "robust",
  "compute_provider": "modal-a100 + baseten-muse-spark-open",
  "plot_url": "/static/plots/c-0142_vcam1.png",
  "verification": {
    "recompute_passed": true,
    "recompute_delta": 0.00001,
    "vision_model": "muse-spark-1.3",
    "vision_passed": true,
    "vision_critique": "Violin plot confirms all 6 disease biopsies exceed the control median with no single-sample outlier driving the effect."
  },
  "urine_biomarker_match": {
    "matched": true,
    "protein_name": "VCAM-1",
    "urine_fold_change_active_ln": 3.4,
    "source_citation": "Stanley et al. 2020 (Nature Communications)"
  },
  "audit_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
}
```

### 4.3 `AuditLogEntry` Payload (`GET /api/audit-log`)

```json
{
  "step_index": 3,
  "timestamp_utc": "2026-11-02T15:22:10Z",
  "agent_role": "verifier",
  "meta_model": "muse-spark-1.3 (Meta API) + muse-glimmer-lora (Fireworks)",
  "tool_called": "verify_plot_with_vision",
  "input_summary": "Inspect plot c-0143_cd3d_planted_artifact.png against claim 'CD3D is upregulated in Podocytes'",
  "output_summary": "REJECTED: Visual inspection shows 74% of transcripts lie outside SAM 3.1 glomerular mask; single biopsy outlier drives mean.",
  "prev_hash": "8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4",
  "entry_hash": "2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae"
}
```

## 5. Parallel Agent Workstreams & Functional Requirements (SRS)

Assign one coding agent to each workstream below. Each workstream includes isolated unit tests so agents can verify their work without waiting on other agents.

### Workstream 1 — Agent 1: Data, Spatial Math & Modal GPU Engine (`/data_engine`)

**Objective:** Prepare the real biological data from [GSE286184](https://pmc.ncbi.nlm.nih.gov/articles/PMC13586693/) and [Stanley et al. (2020)](https://pmc.ncbi.nlm.nih.gov/articles/PMC7198599/), implement the contamination math inspired by [Mitchel et al. (2026)](https://www.rna-seqblog.com/impact-and-correction-of-segmentation-errors-in-spatial-transcriptomics/) and [cellAdmix](https://github.com/kharchenkolab/cellAdmix), and deploy **Modal** serverless GPU jobs (`modal_app.py`) to compute the whitepaper benchmark tables rapidly.

* **FR-1.1 (Hero ROI Extraction):** Write `extract_hero_rois.py` to parse 1 control and 2 diseased kidney samples from [GSE286184](https://pmc.ncbi.nlm.nih.gov/articles/PMC13586693/) containing podocyte markers (`NPHS1`, `NPHS2`, `PODXL`), tubular markers (`LRP2`, `UMOD`), infiltrating immune markers (`CD3D`, `PTPRC`, `CXCL9`, `CXCL10`), and disease-associated markers (`VCAM1`, `ALCAM`, `POSTN`).
* **FR-1.2 (Exclusive-Marker Contamination Metric $C$):** Implement `compute_contamination_rate(cells, transcripts, exclusive_pairs)` in `spatial_math.py`:
  $$C = \frac{1}{|P|} \sum_{(g,h) \in P} \frac{\#\{\text{cells}: x_g > 0 \land x_h > 0\}}{\#\{\text{cells}: x_g > 0 \lor x_h > 0\}}$$
  where $P$ contains mutually exclusive cell-type marker pairs (e.g., `(NPHS1, CD3D)`, `(NPHS2, PTPRC)`, `(PODXL, LRP2)`).
* **FR-1.3 (SAM 3.1 Boundary Clipping & Modal GPU Acceleration):** Implement `apply_sam_boundary_audit(cells, transcripts, sam_polygons)` using `shapely`, wrapped in a `@app.function(gpu="A100")` decorator inside `modal_app.py` (with automatic local CPU fallback) so batch scoring across all biopsies completes in under 30 seconds using your $100 Modal credit.
* **FR-1.4 (Pseudobulk DE & Planted False Claim):** Implement sample-level pseudobulk aggregation in `stats_engine.py` across samples (`n_disease = 6`, `n_control = 3`), labelling each gene as `robust`, `artifact` (significant in `10x Default` but loses significance or shrinks >=50% after audit), or `newly_revealed`. Include one deterministic "Planted False Claim" (`claim_id: "c-0143"`, where a single un-audited outlier biopsy spikes `CD3D` inside podocytes) to showcase the Vision Verifier loop live on screen.
* **FR-1.5 (Urine Proteomics Lookup):** Create `data_engine/fixtures/stanley_2020_urine.json` mapping top urinary proteins from [Stanley et al. (2020)](https://pmc.ncbi.nlm.nih.gov/articles/PMC7198599/) (`VCAM1`, `ALCAM`, `PF4`, `TFPI`, `VSIG4`, `CXCL9`, `CXCL10`) to their encoding gene symbols, active-vs-inactive lupus fold changes, and cellular sources.
* **Definition of Done (Agent 1):** Running `pytest data_engine/` passes and outputs `fixtures/roi_hero.json`, 4 high-DPI dark-themed violin/volcano PNG plots, and a Markdown table of batch metrics ready to paste into Section 6 of the whitepaper.

### Workstream 2 — Agent 2: Meta Model API, Baseten, Fireworks & SAM 3.1 Pipeline (`/meta_models`)

**Objective:** Build the unified multi-provider inference layer combining the [Meta Model API](https://dev.meta.ai/events/global-hackathon) (`https://api.meta.ai/v1`), **Baseten** (`Muse Spark Open`), **Fireworks AI** (`Muse Glimmer` LoRA), and **Modal** (`SAM 3.1` fine-tuning) to lock in the **25% Use of Meta AI Tooling** score.

* **FR-2.1 (Multi-Provider Meta Router & Credit Guardrail):** Implement `MetaClient` in `client.py` routing:
  * Planning (`Muse Wonder`), Plot Vision Verification (`Muse Spark 1.3`), Video Segmentation (`SAM 3.1`), and Speech-to-Text (`Muse Voice Transcribe`) -> [Meta Model API](https://dev.meta.ai/events/global-hackathon) (`https://api.meta.ai/v1`, Standard Mode).
  * High-throughput parallel gene/literature worker calls -> **Baseten** `Muse Spark Open` endpoint (leveraging your $100 credit and 2M TPM rate limit).
  * Evidence-citing cell-type marker annotation -> **Fireworks AI** `Muse Glimmer` endpoint (leveraging your $25 credit).
  * Include an automatic SHA-256 disk-cache (`diskcache` or SQLite) across all three providers so repeated test runs cost $0.00 and serve as an instant fallback during live judging.
* **FR-2.2 (Flagship Feature — `SAM 3.1` Video Tracking Across Slide Tile Seams + Modal Fine-Tune):** To overcome `SAM 3` zero-shot pathology limitations documented in [Kong et al. (2026)](https://arxiv.org/abs/2604.18225), implement `sam_video_stitcher.py`:
  1. Slice a 2,048×2,048 biopsy ROI into a snake-ordered sequence of 16 overlapping 512×512 tiles.
  2. Use your Modal fine-tuned `SAM 3.1` glomerulus head (trained on [HuBMAP Hacking the Kidney](https://www.kaggle.com/competitions/hubmap-kidney-segmentation) PAS tiles) or `Muse Spark 1.3` vision on Tile 0 to seed initial bounding boxes for glomeruli and tubules.
  3. Stream the 16 tiles as sequential video frames into `SAM 3.1` video tracking (`$0.20 / 1,000 frames`) so object IDs persist smoothly across tile seams without boundary fracturing.
  4. Stitch the returned frame masks back into global 2,048×2,048 polygons (`sam31_glomerulus_polygons`).
* **FR-2.3 (Flagship Feature — `Muse Spark 1.3` Multimodal Plot Verifier):** Implement `verify_plot_with_vision(plot_png_path, claim_json)` in `spark_vision_verifier.py`. Send the rendered plot PNG and the structured claim to `Muse Spark 1.3` with a strict JSON schema prompt checking: (a) whether the plotted direction matches `audited_log2fc`, (b) whether a single sample outlier drives the distribution, and (c) whether contamination leakage exceeds the threshold.
* **FR-2.4 (Bonus Open-Weights Feature — `Muse Glimmer` LoRA Cell Annotator on Fireworks):** Implement `glimmer_lora_annotator.py` to format a 300-example JSONL dataset of kidney cell types and canonical marker pairs from [GSE286184](https://pmc.ncbi.nlm.nih.gov/articles/PMC13586693/), trigger a fast LoRA fine-tune of `Muse Glimmer` on Fireworks AI, and expose `annotate_cell_purity(marker_counts)` to flag hybrid contaminated cells.
* **Definition of Done (Agent 2):** All model wrappers (`Meta API`, `Baseten`, `Fireworks`, `Modal`) execute against live endpoints, cache their responses to `/meta_models/cache/`, and return valid `/contracts` schemas.

### Workstream 3 — Agent 3: Multi-Agent MCP Server & Cryptographic Audit Trail (`/agent_server`)

**Objective:** Connect the Data Engine and Multi-Provider Meta Models into a FastAPI + Server-Sent Events (SSE) backend where `Muse Wonder` plans, Baseten `Muse Spark Open` workers execute MCP tools in parallel, the `Muse Spark 1.3` Vision Verifier gates every claim, and every step is hash-chained.

* **FR-3.1 (`Muse Wonder` Checkpointed Planner):** Implement `wonder_planner.py`. When a scientist submits a natural-language or voice question, `Muse Wonder` decomposes it into a 4-stage DAG:
  1. `STAGE_1_SEGMENT_AUDIT`: Run `SAM 3.1` video-tile stitch on Modal/Meta API & score cell purity with Fireworks `Muse Glimmer` LoRA + contamination rate $C$.
  2. `STAGE_2_PSEUDOBULK_DE`: Fan out parallel differential expression worker tasks across Baseten `Muse Spark Open` (2M TPM) comparing `10x Default` vs. `SpatialScout Audit`.
  3. `STAGE_3_VISION_VERIFY`: Recompute statistics from raw counts and inspect every plot PNG via `Muse Spark 1.3` vision (looping back to Stage 2 if a claim fails verification).
  4. `STAGE_4_URINE_OMICS_BRIDGE`: Map verified tissue claims to [Stanley et al. (2020)](https://pmc.ncbi.nlm.nih.gov/articles/PMC7198599/) urinary biomarkers and await PI sign-off.
* **FR-3.2 (Self-Correcting Verification Loop):** In `spark_worker.py`, ensure that during `STAGE_3_VISION_VERIFY`, Claim `c-0143` (`CD3D` in Podocytes) is flagged by both the `SAM 3.1` boundary check and `Muse Spark 1.3` plot vision, emitting a real-time SSE event (`event: claim_rejected_loopback`) before outputting the cleaned final claim list.
* **FR-3.3 (SHA-256 Hash-Chained Audit Log & Notebook Export):** Implement `audit_chain.py` so every tool call appends an `AuditLogEntry` where `entry_hash = sha256(prev_hash + timestamp + model + tool + output_hash)`. Add `GET /api/export-notebook` to download a standalone `.ipynb` file that replays the exact session.
* **FR-3.4 (API Endpoints):**
  * `POST /api/voice` — Accepts audio blob, returns `Muse Voice Transcribe` transcript.
  * `POST /api/analyze/stream` — Streams SSE events (`plan_created`, `sam_tile_progress`, `audit_metric_updated`, `claim_verified`, `claim_rejected_loopback`, `omics_mapped`) so the UI animates live.
  * `GET /api/roi/{roi_id}` — Returns the `SpatialROI` geometry and transcript coordinates.
  * `POST /api/approve` — Logs PI voice/click sign-off into the hash chain.

### Workstream 4 — Agent 4: Split-Screen Interactive Web UI (`/web_ui`)

**Objective:** Build a high-contrast, dark-mode scientific command center (React + Tailwind + HTML5 Canvas) designed specifically to win the **25% Demo** score in the first 30 seconds of the video.

* **FR-4.1 (Top Bar — Voice Command, `Muse Wonder` Live DAG & Infrastructure Telemetry Badges):** Include a pulsing microphone button (`"Hold to Speak to Muse Voice"`), preset 1-click query chips, a 4-node horizontal stepper showing which Meta model is active, and live telemetry pills showing active calls across **Meta Model API**, **Modal A100**, **Baseten (2M TPM)**, and **Fireworks LoRA**.
* **FR-4.2 (Center Stage — Interactive Split-Screen Glomerulus Canvas):** Render the kidney biopsy ROI with an interactive slider or side-by-side split view:
  * **Left Pane (`10x Default Segmentation`):** Shows bloated cell polygons crossing the glomerular border, a red `34.2% Contamination Rate` badge, and false `CD3D` immune transcripts assigned inside podocytes.
  * **Right Pane (`SpatialScout SAM 3.1 Video-Stitched Audit`):** Animates the 4×4 tile seam stitch, draws crisp cyan `SAM 3.1` glomerular boundaries, highlights leaked boundary transcripts in bright yellow with vectors pointing back to their true infiltrating T-cell source, and drops the badge to `3.8% Contamination Rate (89% Reduction)`.
* **FR-4.3 (Right Drawer — Verified Claims, "Caught Lie" Vision Card & Urine Bridge):**
  * Display cards for each candidate gene with badges: `ROBUST (VERIFIED)`, `NEWLY REVEALED`, or `REJECTED: SEGMENTATION ARTIFACT`.
  * Include an expandable **"Muse Spark 1.3 Vision Audit"** panel showing the actual violin/volcano plot image alongside the model's visual critique explaining why `CD3D` in podocytes was rejected and why `VCAM1` passed.
  * Display the **Urine Biomarker Bridge** card linking `VCAM1` and `ALCAM` expression in audited podocytes/endothelial cells directly to non-invasive urinary elevation in active lupus nephritis ([Stanley et al. 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7198599/)).
* **FR-4.4 (Bottom Bar — Cryptographic Audit Trail & Instant Judge Replay Toggle):** Include a live scrolling ticker of SHA-256 hash-chained agent actions, an **"Export Reproducible Notebook (.ipynb)"** button, and a **"Cached Replay Mode"** toggle so judges clicking the public URL between November 4 and November 8 get a guaranteed zero-latency experience.

## 6. Prompts to Copy-Paste Into Your Coding Agents (`Muse Code` / Sub-Agents)

Once `/contracts/models.py` and `/contracts/types.ts` are created, spawn four parallel terminal sessions and feed each agent its prompt below:

* **Prompt for Agent 1 (Data, Spatial Math & Modal GPU Engine):**
  > "Read `SpatialScout_PRD_SRS_Spec.md` Section 4 and Workstream 1. Build `/data_engine` adhering strictly to `/contracts/models.py`. Generate `fixtures/roi_hero.json` from GSE286184 marker profiles and `fixtures/stanley_2020_urine.json`, implement exclusive-marker contamination rate $C$ and Shapely boundary clipping against SAM 3.1 polygons with Modal serverless GPU acceleration (`modal_app.py`) and local CPU fallback, render high-DPI dark-mode plots for `VCAM1`, `ALCAM`, `NPHS1`, and the planted `CD3D` artifact, and output the completed Markdown results tables for the whitepaper."
* **Prompt for Agent 2 (Meta API, Baseten, Fireworks & SAM 3.1 Vision):**
  > "Read `SpatialScout_PRD_SRS_Spec.md` Section 4 and Workstream 2. Build `/meta_models` with deterministic SHA-256 disk caching across Meta Model API (`https://api.meta.ai/v1` in Standard Mode), Baseten (`Muse Spark Open` at 2M TPM), and Fireworks AI (`Muse Glimmer` LoRA cell annotator). Implement `sam_video_stitcher.py` (slicing a 2048x2048 biopsy image into a 16-frame snake tile video for SAM 3.1 tracking and re-stitching global polygons), `spark_vision_verifier.py` (multimodal plot inspection with Muse Spark 1.3), `glimmer_lora_annotator.py`, and `voice_transcriber.py`."
* **Prompt for Agent 3 (FastAPI, MCP & Hash-Chained Verifier):**
  > "Read `SpatialScout_PRD_SRS_Spec.md` Section 4 and Workstream 3. Build `/agent_server` in FastAPI. Wire `Muse Wonder` to generate the 4-stage analysis plan, Baseten `Muse Spark Open` workers to fan out parallel MCP tool calls in `/data_engine` and `/meta_models`, the `Muse Spark 1.3` self-correcting verification loop that rejects planted artifact claims when recomputation or plot vision fails, the SHA-256 hash-chained audit log, and the SSE streaming endpoint `POST /api/analyze/stream`."
* **Prompt for Agent 4 (Split-Screen Web UI):**
  > "Read `SpatialScout_PRD_SRS_Spec.md` Section 4 and Workstream 4. Build `/web_ui` in React, TypeScript, and Tailwind CSS against `/contracts/types.ts`. Build the Voice Command Bar with live telemetry badges for Meta API, Modal, Baseten, and Fireworks; the interactive Split-Screen Glomerulus Canvas (10x Default vs. SAM 3.1 Video-Stitched Audit highlighting yellow leaked transcripts); the Claims & Spark 1.3 Vision Verifier drawer; the Urine Biomarker Bridge card; and a 1-click Offline Verified Replay mode for hackathon judges."

## 7. Final 48-Hour Sprint Checklist (Nov 2 – Nov 4, 2026 Cutoff)

* [ ] **Eligibility & Team Listing Verified:** Confirm all teammates have accepted invitations on the [Meta Global AI Developer Hackathon page](https://cerebralvalley.ai/e/meta-ai-developer-hackathon) and that university lab testers are credited strictly as external study participants in Section 7, not unlisted entrants.
* [ ] **Whitepaper Placeholders Removed:** Replace every `[TO MEASURE]` and `[PENDING]` tag in `SpatialScout Whitepaper.docx` with the exact numbers output by `data_engine/scripts/run_batch_benchmarks.py` and export to `SpatialScout_Whitepaper.pdf` in the root of the GitHub repo.
* [ ] **2-Minute Demo Video Recorded & Hosted:** Record the 4-beat Golden Path walkthrough showing voice input, the `SAM 3.1` tile-to-video seam stitch, the split-screen yellow transcript leak reveal, and `Muse Spark 1.3` rejecting the planted outlier plot.
* [ ] **Public URL Protected by Replay Cache:** Deploy `/web_ui` and `/agent_server` with disk-cached API responses enabled by default so live judges between November 4 and November 8 experience zero API rate-limit errors or broken screens.