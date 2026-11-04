# Revision 3 (draft for validation): Dual-Biopsy Microscope & Hypothesis Tester

> **Status:** adopted Nov 3 and recorded on the spec issue #1. Its work is tickets 02b (#18), 02c (#19) and 10b (#20), the hypothesis verdict banner.
>
> **Source:** `docs/spec/directive-agentic-spatial-lab.md` and `docs/spec/directive-dual-biopsy.md` (Nov 3). Adopted with the corrections in §6; the directives themselves are kept as received and are not specifications.

## 1. The product after this revision

SpatialScout becomes an interactive dual-biopsy microscope and hypothesis tester:

1. **Two biopsies side by side.** A control section on the left, a diseased section on the right, each a multichannel image with toggleable channels.
2. **One ROI per biopsy.** The researcher drags a box on each.
3. **A hypothesis.** Typed, spoken, or chosen from the hypothesis chips.
4. **Segmentation.** The plan runs SAM 3.1 inside each box, using the dragged box as SAM's box prompt.
5. **Boundary de-contamination.** A slider moves from the default condition to stricter conditions. Excluded molecules light yellow, with retention and thinning expectations beside every number.
6. **A verdict banner.** It reads CONFIRMED, REFUTED or INCONCLUSIVE, and the verdict is verified.

## 2. Data layers (what is real, and what each can prove)

| Layer | Source | Status (probed Nov 3) | What it can and cannot support |
| --- | --- | --- | --- |
| **A. Rendered molecule images** (cohort context and RNA-level audit) | GSE286184: 21 distinct Xenium sections, already ingested | Ready | One channel per marker group, rendered from molecule coordinates: nuclei, NPHS1, LRP2/CUBN, UMOD, CD3D/CD8A/MS4A1, POSTN. Every pane is labelled "rendered from molecules". The audit, thinning controls and verdicts run here. |
| **B. Real CODEX microscopy** (primary viewer, chosen Nov 3) | KPMP CODEX `image_collection*.zip` (tif + csv, 2.7–10 GB each, open access) | Access confirmed; antibody panel not yet checked | Real fluorescence images plus per-cell protein tables, with real per-participant clinical metadata. **Different people and a different assay (protein) from GSE286184**, so molecules are never overlaid on these images. A hypothesis about RNA genes such as LRP2, CUBN or UMOD can be tested here only if the panel has those antibodies. |
| **C. HuBMAP PhenoCycler** | HBM234.XKZT.245, a 66-year-old male reference donor | Record is public, files return 403 without login | At most a healthy-side image. Dropped unless public file access is found. |

Any clinical value shown in the UI (eGFR, proteinuria, KDIGO stage) comes from KPMP's downloaded metadata files. None is ever typed in.

### Decision (Nov 3): KPMP CODEX is the primary viewer

The two viewports open one KPMP healthy-reference participant and one KPMP diseased participant: real `.tif` channels, their per-cell tables, and their real clinical metadata. GSE286184 stays as the RNA-level audit and cohort context, in its own panel labelled with its own sections, never overlaid on the KPMP images.

The verdict on KPMP ROIs uses the protein analogue of the audit:

- **Per-cell marker signal under default segmentation vs a nucleus-restricted measurement**, where the expression matrix or the segmentation masks provide one. Lateral spillover between neighbouring cells is the protein counterpart of molecule admixture.
- **A neighbour-proximity check:** is a cell's foreign-marker signal explained by a bordering cell of the marker's home type?
- **A thinning analogue:** a random-pixel-loss expectation, defined once the CODEX tables are inspected.

Which sub-claims can be tested on KPMP depends on the antibody panel. Sub-claims whose markers are missing from the panel run on GSE286184 only, and the verdict banner says which dataset each sub-claim came from.

**Blocking input:** one control's and one diseased participant's `*_antibody_panel.csv`, provided by the user. After that, download one `image_collection*.zip` each, the smallest that fits: 31-10013 is 2.71 GB.

## 3. Spec changes

- **ROI-scoped audit.** Every audit result can be scoped to an ROI: a box in section coordinates. Fixed populations, conditions, both thinning expectations, neighbour-proximity shares and gates are computed inside the box.
- **Gate readout while dragging.** As the researcher drags, the UI shows the gate status live, for example "23 podocytes · 7 LRP2 molecules · below molecule gate". A box that fails the gates is shown as failing, never hidden.
- **SAM 3.1 on the selected box.** The ROI box becomes SAM's box prompt on the rendered nucleus image, the path that passed spike 3. NPHS1-cluster seeding remains for automatic glomerulus finding. SAM stays an exploratory condition (ADR-0006).
- **Hypothesis verdict.** A plan decomposes each hypothesis into testable sub-claims, for example "podocyte LRP2/CUBN presence persists" and "UMOD in B cells persists". Each sub-claim's verdict is computed by the frozen rules, in these ROIs and under these controls:

  | Verdict | Meaning |
  | --- | --- |
  | **CONFIRMED** | The predicted direction holds under every valid primary condition, and the required controls are cited and pass. |
  | **REFUTED** | The sub-claim is segmentation-sensitive (an excess drop beyond the home-matched expectation) or reverses. |
  | **INCONCLUSIVE** | The evidence is insufficient: the gates fail, or the controls are missing. |

  The banner always reads "in these ROIs, under these controls". Any outcome renders; none is written in advance.
- **Two levels, kept apart.**
  - **ROI vs ROI** compares one person's section with another's. It is descriptive only.
  - **Cohort context:** the same measure across the 21 distinct sections, with leave-one-section-out, shown beside it. Both levels carry their inference eligibility.
- **Hypothesis chips.** Directive chips 1–3 are adopted, phrased as questions with no expected answers. Chip 4 (cross-disease) becomes a roadmap slide, not a loaded dataset.
- **Precision research card.** It lists the verified sub-claims and a VCAM1 "candidate tissue association" note (Stanley 2020), badged "Research hypothesis, not clinical advice". No drug or pathway recommendations.

## 4. Ticket changes

- **New 02b: Dual-biopsy viewer with rendered channels and ROI selection** (blocked by #3; already closed).
  - Multichannel rendering per section, with channel toggles.
  - Two synchronised viewports and an ROI box tool on each.
  - The live gate readout.
  - Default pair: Control x2 vs DKD x3.
  - **Acceptance:** two whole sections render side by side; dragging a box returns its gate status within 200 ms; the "rendered from molecules" label is always visible.
- **New 02c (primary): KPMP CODEX dataset store and real-image viewer.** First check the antibody panel CSV (3 kB) of one control and one diseased participant. Download one image collection each only if the hypothesis markers, or close protein proxies, are present.
  - Ingest one healthy-reference and one diseased participant: their channel images, converted to tiled WebP or PNG layers per channel for the browser and with the raw TIFF kept downloadable; their per-cell tables; their segmentation where available; their clinical metadata.
  - The dual viewports open on these two participants, with an ROI box tool and channel toggles.
  - **Acceptance:** both real images render side by side, the clinical values shown trace to KPMP's files, and nothing from GSE286184 is drawn on them.
- **05 (#6):** adds ROI scoping to every audit operation and an `roi` field on audit results. The agent's partial work resumes; nothing is discarded.
- **06 (#7):** adds ROI-vs-ROI descriptive comparison next to cohort context. Still no p-values (ADR-0007).
- **07 (#8):** the user's ROI box can be sent to SAM as its box prompt. Outlines stay exploratory.
- **09a (#10):** the plan decomposes a hypothesis into sub-claims. Muse Spark 1.3 still chooses the controls.
- **10 (#12):** the verdict banner. Each sub-claim's verdict derives from its verified claims; a claim that failed or is disputed can never produce CONFIRMED. "Challenge the verifier" stays.

## 5. Unchanged

- Persisted investigations and run modes.
- Gateway gating and budget.
- Voice: #9 resumes unchanged.
- Modal deployment.
- Every frozen rule in the spec.

## 6. Corrections to the directive (needed to stay within ADR-0001)

| Directive text | Why it cannot ship | Replacement |
| --- | --- | --- |
| "3.2x higher", "drops by 82%", "collapses by >75%", "more than 3x steeper" | Results written before they are computed | The verdict renders whatever the pipeline computes |
| "Patient #DKD-04 (eGFR 38, proteinuria 3.4 g/g, KDIGO 3b)" from GSE286184 | Invented clinical data. GSE286184 has no clinical metadata | Section names only (for example "DKD section x3"); real clinical values only from KPMP files |
| Q4 answer: podocyte rule uses NPHS2, PODXL and WT1 | Those genes are not in the 50-gene panel | "NPHS1-anchored rule without LRP2/CUBN, plus the label-sensitivity check" |
| GSE286184 coordinates "paired with" KPMP or HuBMAP `.tif` images | Different donors and assays | Separate layers (§2) |
| Muse Glimmer LoRA firing live on Fireworks | Needs an on-demand deployment, about $8 an hour | Stretch ticket 14, offline only |
| "Parallel spatial math on Modal GPUs" | The math is CPU NumPy | "Batch audit on Modal" |
| Loaded Alzheimer's and tonsil datasets | Not ingested, and no time to | Roadmap slide |
