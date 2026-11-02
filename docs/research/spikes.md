# De-risking spikes (Nov 2 2026)

Three throwaway spikes run on real data and live Meta models before writing the spec. Code is in `spikes/`; outputs land in `spikes/out/` (not committed). Numbers below are spike-grade: a quick marker rule, no PyDESeq2, no shrinkage. The product pipeline recomputes everything.

## 1. Science spike: PASS (feasible, honest, not dramatic)

Setup: GSE286184 control (x1, x2, x6) vs DKD (x3, x4, x5, x7, x8, x9) sections. Molecules filtered to `qv ≥ 20` and the 50 panel genes. Cells annotated once from default counts with a one-or-two-marker-per-compartment rule (`spikes/science_spike.py`), labels frozen across conditions. Conditions: **default** (`cell_id`), **nucleus-only** (`overlaps_nucleus == 1`), **distance caps** (non-nuclear molecules within 1 or 2 µm of the nucleus kept).

Retention (mean over sections): nucleus-only keeps 55% of assigned molecules, the 1 µm cap 74%, the 2 µm cap 86%.

### The published "Podocyte endocytosis" state is assignment-stable

| Condition | Molecules kept | Podocyte NPHS1 kept | Podocyte LRP2 kept | Podocyte CUBN kept | Podocytes LRP2+ or CUBN+ |
| --- | --- | --- | --- | --- | --- |
| default | 100% | 100% | 100% | 100% | 17.6% |
| nucleus-only | 55.4% | 75.0% | 71.8% | 68.8% | 13.6% |
| cap 1 µm | 74.1% | 86.0% | 83.5% | 86.2% | 15.9% |

Podocyte LRP2/CUBN molecules are lost at about the same rate as the podocytes' own NPHS1. Their nuclear fraction (LRP2 in podocytes 0.72) matches LRP2 in its home proximal-tubule cells (0.76) and NPHS1 in podocytes (0.75). Neighbour admixture from the expansion zone would show a much lower nuclear fraction. Caveat: 2D nuclear overlap cannot exclude molecules from a cell lying above or below the nucleus in z.

### DKD vs Control across all 650 (cell type, gene) pairs

Gate: every section needs ≥ 10 molecules of the gene in that cell type and ≥ 20 cells; leave-one-section-out must keep the default direction. Sensitive means a log2 effect range > 0.5 across conditions, or a direction flip.

| Label | Count |
| --- | --- |
| insufficient evidence | 544 |
| stable | 103 |
| segmentation-sensitive | 3 |

- Sensitive: UMOD in B cells (−0.66 default → −2.08 nucleus-only; UMOD is the most abundant TAL transcript), JUN in PT and in myeloid cells (−0.81 → −0.29).
- Stable, large effects: FKBP5, ZFP36, JUN, ZBTB16 lower in DKD across many types (stress/immediate-early genes, plausibly tissue handling); C3 higher in DKD in PT (+1.39) and myeloid cells (+1.45); TNFAIP2 higher in collecting-duct principal cells (+1.50).
- Podocytes are rare (37–209 per section). Apparent podocyte reversals (PECAM1 +0.33 → −0.51, POSTN +0.67 → −0.42) rest on 0–34 molecules per section, so they are **insufficient evidence**, not findings. Count gates are mandatory.
- No section-level p-value survives at 3 vs 6 sections; labels must not depend on significance.

Implication: the demo must not promise a disappearing disease signal. The real story is "most effects hold, a few are sensitive, many are under-powered, and the published podocyte claim survives".

## 2. SAM spike: concept prompts FAIL, box prompts PASS

Section x2, a 1 mm crop with the highest NPHS1 density, rendered gene-agnostically at 1 px = 1 µm: nucleus discs from the cells table (H&E-like colours), and a nuclear-molecule density image.

- **Concept prompts** (`glomerulus`, `round cluster of cells`, `blob`) on both renderings: 0 objects in 6 calls (0.7–2.5 s each).
- **Spark 1.3 proposing boxes** on the disc rendering: 0 boxes. It read the field as tubules. The crop has three glomeruli, visible as NPHS1 + PECAM1 clusters. Without cytoplasm and Bowman's space the rendering does not look like a glomerulus.
- **NPHS1-cluster boxes → SAM 3.1 box prompts**: 7 masks in 3.8 s. Validation by glomerular-tuft genes the seeding never saw:

| Region | Area of crop | PECAM1 enrichment | PDGFRB enrichment | UMOD | LRP2 |
| --- | --- | --- | --- | --- | --- |
| Seed boxes | 4.0% | ×6.5 | ×13.2 | ×0.04 | ×0.18 |
| SAM 3.1 masks | 2.1% | ×10.5 | ×18.4 | ×0.07 | ×0.30 |

SAM tightens crude boxes into masks that concentrate tuft genes and exclude tubule genes. Masks were fragmented because DBSCAN split glomeruli into several clusters; merge clusters (one box per glomerulus) before prompting. NPHS1 cannot validate these masks because it seeded them. Do not claim independent validation; claim PECAM1/PDGFRB consistency.

## 3. Vision spike: PASS (3/3)

Real per-section plot (C3 in PT cells, default condition, Control n = 3 vs DKD n = 6), schema-constrained verdict from `muse-spark-1.3` at `reasoning_effort: low`.

| Case | Expected | Verdict | Latency |
| --- | --- | --- | --- |
| Correct plot | direction and counts match | PASS (higher = DKD, n = 6 vs 3) | 5.5 s |
| Group labels swapped | direction mismatch | PASS ("Control mean bar is above DKD … opposite of claimed") | 7.2 s |
| One DKD section dropped | count mismatch | PASS ("5 red points, not 6 DKD as claimed") | 3.8 s |

Plot design that worked: two groups, one point per section, a black mean bar, `group (n=k)` tick labels, the gene and cell type in the title.
