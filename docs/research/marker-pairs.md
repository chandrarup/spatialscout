# Frozen exclusive marker pairs (Nov 2 2026)

`configs/exclusive_marker_pairs.json` is the frozen artifact the co-expression score uses. It was built by `spikes/freeze_marker_pairs.py` from the GSE271188 single-nucleus reference before any Xenium evaluation, and it records the source checksums.

- **Reference:** two control donors, GSM8371526 (kidney_snRNA_14, 10,000 nuclei) and GSM8371535 (kidney_snRNA_23, 14,460 nuclei); "diagnosis: Control" per [GEO](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE271188).
- **Candidates:** 117 pairs of panel markers for different compartments (16 markers, the same compartment map as the spike's label rule).
- **Rule:** in every donor, nuclei detecting both genes must be under 1% of nuclei detecting either, and at least 300 nuclei must detect either.
- **Result:** **40 pairs frozen**; 77 rejected (58 co-detected at 1% or more, 19 with too little support). Frozen pairs are mostly immune markers (CD3D, CD8A, MS4A1, CD68, ITGAX) against epithelial or endothelial markers.

## Bearing on the hero question

NPHS1 is **not** exclusive with the proximal-tubule markers in this reference:

| Pair | GSM8371526 both / either | Rate | GSM8371535 both / either | Rate |
| --- | --- | --- | --- | --- |
| NPHS1, LRP2 | 225 / 6,953 | 3.2% | 421 / 4,157 | 10.1% |
| NPHS1, CUBN | 252 / 8,557 | 2.9% | 598 / 4,825 | 12.4% |

Single-nucleus data has no image segmentation step, so this co-detection cannot come from Xenium assignment. It can come from ambient RNA or doublets, which single-nucleus data is known for, so it is a consistency signal, not confirmation of a podocyte state. It also means these pairs are excluded from the admixture proxy, so the co-expression score never counts the hero co-expression as admixture by construction.
