"""The two frozen label rules: cell type labels assigned once from default counts (ADR-0002).

Both rules read a cell's default-condition molecules (every molecule the instrument assigned to it) and score
each cell type as its best marker's count divided by that gene's scale. The gene scale is the mean count of
the gene per expressing cell, pooled over the control sections.

- **Full-panel rule** (`full-panel-v1`), ported from the science spike: a cell with fewer than 5 molecules is
  "Low quality"; otherwise it takes the top-scoring cell type if that score reaches 0.5, else "Unlabelled".
  Ties go to the cell type listed first in `MARKERS`.
- **NPHS1-anchored podocyte rule** (`nphs1-anchored-v1`): podocyte membership is decided with LRP2 and CUBN
  ignored entirely. A cell is a podocyte when, counting only its other molecules, it has at least 5 and NPHS1
  is its top-scoring marker at 0.5 or more. Every other cell keeps its full-panel label, except a full-panel
  podocyte that fails this test, which becomes "Unlabelled". The panel has no NPHS2, PODXL or WT1, so NPHS1 is
  the only podocyte marker. Neither rule is free of selection bias: this one can admit proximal-tubule cells
  that carry stray NPHS1.
"""

from collections.abc import Iterable, Sequence

import pandas as pd

from ..contracts import LabelCounts, LabelRule

FULL_PANEL_RULE = "full-panel-v1"
NPHS1_ANCHORED_RULE = "nphs1-anchored-v1"
LABEL_RULES = (FULL_PANEL_RULE, NPHS1_ANCHORED_RULE)

# One or two specific markers per cell type, from the 50-gene panel, in tie-break order (spike marker map).
MARKERS: dict[str, list[str]] = {
    "Podocyte": ["NPHS1"],
    "PEC": ["ALDH1A2"],
    "PT": ["LRP2", "CUBN"],
    "TAL": ["UMOD"],
    "DCT": ["SLC12A3"],
    "PC": ["AQP2"],
    "IC": ["SLC4A1"],
    "Endothelial": ["PECAM1"],
    "Mesangial/Pericyte": ["PDGFRB"],
    "Fibroblast": ["COL1A1"],
    "T cell": ["CD3D", "CD8A"],
    "B cell": ["MS4A1"],
    "Myeloid": ["CD68", "ITGAX"],
}
SCORE_THRESHOLD = 0.5
MIN_MOLECULES = 5
ANCHOR_IGNORED_GENES = ("LRP2", "CUBN")
PODOCYTE = "Podocyte"
LOW_QUALITY = "Low quality"
UNLABELLED = "Unlabelled"


def rule_specs() -> list[LabelRule]:
    """The frozen rules as recorded in every label artifact."""
    return [
        LabelRule(
            label_rule_id=FULL_PANEL_RULE,
            description=(
                "Each cell type scores its best marker's default count divided by the gene scale. Fewer than "
                f"{MIN_MOLECULES} default molecules: 'Low quality'. Otherwise the top score's cell type if it reaches "
                f"{SCORE_THRESHOLD}, else 'Unlabelled'. Ties go to the cell type listed first."
            ),
            markers=MARKERS,
            ignored_genes=[],
            score_threshold=SCORE_THRESHOLD,
            min_molecules=MIN_MOLECULES,
        ),
        LabelRule(
            label_rule_id=NPHS1_ANCHORED_RULE,
            description=(
                "Podocyte membership ignores LRP2 and CUBN entirely: a cell is a podocyte when, counting only its "
                f"other molecules, it has at least {MIN_MOLECULES} and NPHS1 is its top-scoring marker at "
                f"{SCORE_THRESHOLD} or more. Other cells keep their full-panel label; a full-panel podocyte that fails "
                "this test is 'Unlabelled'. It can admit proximal-tubule cells carrying stray NPHS1."
            ),
            markers={cell_type: [g for g in genes if g not in ANCHOR_IGNORED_GENES] for cell_type, genes in MARKERS.items()},
            ignored_genes=list(ANCHOR_IGNORED_GENES),
            score_threshold=SCORE_THRESHOLD,
            min_molecules=MIN_MOLECULES,
        ),
    ]


def pool_gene_scales(sections: Iterable[pd.DataFrame]) -> dict[str, float]:
    """Mean default count of each gene per expressing cell, pooled over sections. Cells are keyed by section and
    cell id, because Xenium cell ids repeat across sections."""
    per_cell = [_default_counts(molecules).stack() for molecules in sections]
    pooled = pd.concat(per_cell) if per_cell else pd.Series(dtype=float)
    expressing = pooled[pooled > 0]
    return {str(gene): float(value) for gene, value in expressing.groupby(level="gene").mean().sort_index().items()}


def apply_label_rules(molecules: pd.DataFrame, cell_ids: Sequence[str], gene_scales: dict[str, float]) -> pd.DataFrame:
    """Labels for every cell under both rules: a frame indexed by cell id, one column per rule id."""
    counts = _default_counts(molecules).reindex(index=pd.Index(list(cell_ids), name="cell_id"), fill_value=0)
    full = _full_panel(counts, gene_scales)
    anchored_podocyte = _anchored_podocyte(counts, gene_scales)
    anchored = full.where(full != PODOCYTE, UNLABELLED).where(~anchored_podocyte, PODOCYTE)
    return pd.DataFrame({FULL_PANEL_RULE: full, NPHS1_ANCHORED_RULE: anchored})


def label_counts(labels: pd.DataFrame) -> LabelCounts:
    first, second = labels[FULL_PANEL_RULE], labels[NPHS1_ANCHORED_RULE]
    changed = first != second
    transitions = (first[changed] + " -> " + second[changed]).value_counts()
    return LabelCounts(
        cells=len(labels),
        cell_types={rule: {str(k): int(v) for k, v in sorted(labels[rule].value_counts().items())} for rule in LABEL_RULES},
        differing_cells=int(changed.sum()),
        differing={str(k): int(v) for k, v in sorted(transitions.items())},
    )


def _default_counts(molecules: pd.DataFrame) -> pd.DataFrame:
    """Default-condition molecules per cell and gene (cells without molecules are absent)."""
    assigned = molecules[molecules["cell_id"].notna()]
    counts = assigned.groupby(["cell_id", "gene"], observed=True).size().unstack(fill_value=0)
    counts.index = counts.index.astype(str)
    counts.columns = counts.columns.astype(str)
    counts.columns.name = "gene"
    return counts


def _scores(counts: pd.DataFrame, gene_scales: dict[str, float], ignored: Sequence[str] = ()) -> pd.DataFrame:
    """Per cell type, the best marker's count divided by its gene scale; 0 for a marker never seen."""
    scores = {}
    for cell_type, genes in MARKERS.items():
        usable = [g for g in genes if g not in ignored]
        if not usable:
            continue
        per_gene = [counts[g] / gene_scales[g] if g in counts and g in gene_scales else pd.Series(0.0, index=counts.index) for g in usable]
        scores[cell_type] = pd.concat(per_gene, axis=1).max(axis=1)
    return pd.DataFrame(scores, index=counts.index)


def _full_panel(counts: pd.DataFrame, gene_scales: dict[str, float]) -> pd.Series:
    scores = _scores(counts, gene_scales)
    labels = scores.idxmax(axis=1).where(scores.max(axis=1) >= SCORE_THRESHOLD, UNLABELLED)
    labels[counts.sum(axis=1) < MIN_MOLECULES] = LOW_QUALITY
    return labels.astype(str)


def _anchored_podocyte(counts: pd.DataFrame, gene_scales: dict[str, float]) -> pd.Series:
    """Podocyte membership read only from genes other than LRP2 and CUBN."""
    others = counts.drop(columns=[g for g in ANCHOR_IGNORED_GENES if g in counts])
    scores = _scores(others, gene_scales, ignored=ANCHOR_IGNORED_GENES)
    return (
        (others.sum(axis=1) >= MIN_MOLECULES)
        & (scores.idxmax(axis=1) == PODOCYTE)
        & (scores[PODOCYTE] >= SCORE_THRESHOLD)
    )
