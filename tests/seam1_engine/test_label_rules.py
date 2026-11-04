"""Seam 1: the two frozen label rules on a hand-built molecule table, with labels worked out by hand.

Gene scales are given, so each marker score is a count divided by a round number:
NPHS1 2, LRP2 2, CUBN 2, UMOD 4, PECAM1 2 (JUN is on the panel but marks no cell type).

| cell | default molecules            | full-panel rule              | NPHS1-anchored rule                       |
| ---- | ---------------------------- | ---------------------------- | ----------------------------------------- |
| A    | NPHS1 6                      | Podocyte (3.0)               | Podocyte                                  |
| B    | NPHS1 4, LRP2 10, UMOD 1     | PT (LRP2 5.0 beats NPHS1 2.0) | Podocyte: ignoring LRP2/CUBN, 5 molecules, NPHS1 2.0 tops UMOD 0.25 |
| C    | UMOD 8                       | TAL (2.0)                    | TAL                                       |
| D    | NPHS1 3                      | Low quality (3 < 5)          | Low quality                               |
| E    | none                         | Low quality (0 < 5)          | Low quality                               |
| F    | JUN 5                        | Unlabelled (no score >= 0.5) | Unlabelled                                |
| G    | NPHS1 3, CUBN 3              | Podocyte (tie 1.5 with PT; Podocyte comes first) | Unlabelled: ignoring LRP2/CUBN, 3 < 5 molecules |
| H    | NPHS1 2, PECAM1 6            | Endothelial (3.0 beats 1.0)  | Endothelial (NPHS1 is not its top marker) |

Unassigned molecules (an NPHS1 molecule with no cell) never count toward any cell.
"""

import pandas as pd
import pytest

from spatialscout.data import FULL_PANEL_RULE, NPHS1_ANCHORED_RULE, apply_label_rules, label_counts, pool_gene_scales

SCALES = {"NPHS1": 2.0, "LRP2": 2.0, "CUBN": 2.0, "UMOD": 4.0, "PECAM1": 2.0, "JUN": 1.0}
CELLS = ["A", "B", "C", "D", "E", "F", "G", "H"]
COUNTS = {
    "A": {"NPHS1": 6},
    "B": {"NPHS1": 4, "LRP2": 10, "UMOD": 1},
    "C": {"UMOD": 8},
    "D": {"NPHS1": 3},
    "E": {},
    "F": {"JUN": 5},
    "G": {"NPHS1": 3, "CUBN": 3},
    "H": {"NPHS1": 2, "PECAM1": 6},
}


def molecules(counts):
    rows = [{"cell_id": cell, "gene": gene} for cell, genes in counts.items() for gene, n in genes.items() for _ in range(n)]
    rows.append({"cell_id": None, "gene": "NPHS1"})
    return pd.DataFrame(rows).astype("string")


@pytest.fixture(scope="module")
def labels():
    return apply_label_rules(molecules(COUNTS), CELLS, SCALES)


def test_the_full_panel_rule_labels_each_cell_by_its_top_marker_score(labels):
    assert labels[FULL_PANEL_RULE].to_dict() == {
        "A": "Podocyte", "B": "PT", "C": "TAL", "D": "Low quality", "E": "Low quality",
        "F": "Unlabelled", "G": "Podocyte", "H": "Endothelial",
    }


def test_the_anchored_rule_decides_podocytes_without_lrp2_or_cubn(labels):
    assert labels[NPHS1_ANCHORED_RULE].to_dict() == {
        "A": "Podocyte", "B": "Podocyte", "C": "TAL", "D": "Low quality", "E": "Low quality",
        "F": "Unlabelled", "G": "Unlabelled", "H": "Endothelial",
    }


def test_adding_lrp2_and_cubn_never_changes_anchored_podocyte_membership():
    flooded = {cell: {**genes, "LRP2": genes.get("LRP2", 0) + 40, "CUBN": genes.get("CUBN", 0) + 40} for cell, genes in COUNTS.items()}
    labels = apply_label_rules(molecules(flooded), CELLS, SCALES)

    assert sorted(labels.index[labels[NPHS1_ANCHORED_RULE] == "Podocyte"]) == ["A", "B"]
    assert set(labels[FULL_PANEL_RULE]) <= {"PT"}


def test_label_counts_record_each_rule_and_the_cells_whose_label_differs(labels):
    counts = label_counts(labels)

    assert counts.cell_types[FULL_PANEL_RULE] == {"Endothelial": 1, "Low quality": 2, "PT": 1, "Podocyte": 2, "TAL": 1, "Unlabelled": 1}
    assert counts.cell_types[NPHS1_ANCHORED_RULE] == {"Endothelial": 1, "Low quality": 2, "Podocyte": 2, "TAL": 1, "Unlabelled": 2}
    assert counts.cells == 8
    assert counts.differing_cells == 2
    assert counts.differing == {"PT -> Podocyte": 1, "Podocyte -> Unlabelled": 1}


def test_gene_scales_pool_cells_from_every_control_section_without_merging_repeated_cell_ids():
    # Xenium cell ids repeat across sections: c1 in section 1 and c1 in section 2 are different cells.
    section_1 = pd.DataFrame({"cell_id": ["c1", "c1", None], "gene": ["NPHS1", "NPHS1", "NPHS1"]}).astype("string")
    section_2 = pd.DataFrame({"cell_id": ["c1"] * 4 + ["c2"] * 6 + ["c2"], "gene": ["NPHS1"] * 10 + ["UMOD"]}).astype("string")

    scales = pool_gene_scales([section_1, section_2])

    # NPHS1 in three expressing cells, with 2, 4 and 6 molecules; UMOD in one cell, with 1.
    assert scales == {"NPHS1": 4.0, "UMOD": 1.0}
