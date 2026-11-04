"""Build the synthetic section SYN-01, whose answers are known by construction.

Usage:  uv run python scripts/build_synthetic_section.py      (rewrites fixtures/synthetic/; deterministic)

Construction, in micrometres, on a 200 x 150 section:
- 12 cells. Inside one glomerulus outline: 3 podocytes, 1 endothelial and 1 mesangial cell. Outside it:
  4 proximal-tubule (PT) cells, 2 thick-ascending-limb (TAL) cells and 1 T cell.
- Every cell has 15 molecules over its nucleus (overlaps_nucleus = 1) and 5 in its expansion zone
  (overlaps_nucleus = 0, within 5 um of the nucleus edge), so 240 molecules are assigned.
- Podocyte C03 faces PT cell C06. C03's 5 expansion-zone molecules are 1 NPHS1 and 4 LRP2 on the side
  facing C06: the default condition counts the LRP2 toward the podocyte, and nucleus-only excludes them.
- 60 unassigned molecules lie outside every cell. Every molecule has qv >= 20.

Two label rules, both by construction: `synthetic-by-construction` (the default, as listed in CELLS) and
`synthetic-alternative`, which also labels PT cell C06 as Podocyte, so a label-sensitivity check on SYN-01 has
exactly one cell the rules disagree on (podocytes: 3 under the default rule, 4 under the alternative).

Known answers (asserted in tests/seam1_engine/test_synthetic_section.py): the default condition counts
240 molecules and nucleus-only keeps 180 (retention 0.75, 60 excluded); every cell type keeps 0.75;
podocyte LRP2 goes from 4 to 0 and podocyte NPHS1 from 56 to 45.
"""

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "fixtures" / "synthetic"
DATASET_ID = "synthetic"
SECTION_ID = "SYN-01"
EXTENT = [0.0, 0.0, 200.0, 150.0]  # x0, y0, x1, y1
EXPANSION_UM = 5.0
GLOMERULUS_CENTRE = (60.0, 75.0)
SEED = 20261102

# cell_id, cell type label, x, y, nucleus radius
CELLS = [
    ("C01", "Podocyte", 46.0, 86.0, 3.0),
    ("C02", "Podocyte", 70.0, 92.0, 3.0),
    ("C03", "Podocyte", 78.0, 70.0, 3.0),
    ("C04", "Endothelial", 52.0, 64.0, 2.5),
    ("C05", "Mesangial", 62.0, 78.0, 2.5),
    ("C06", "PT", 104.0, 70.0, 4.0),
    ("C07", "PT", 125.0, 35.0, 4.0),
    ("C08", "PT", 150.0, 62.0, 4.0),
    ("C09", "PT", 132.0, 105.0, 4.0),
    ("C10", "TAL", 172.0, 118.0, 3.5),
    ("C11", "TAL", 182.0, 28.0, 3.5),
    ("C12", "T cell", 22.0, 130.0, 2.0),
]
# Genes of each cell type's 15 nuclear and 5 expansion-zone molecules.
GENES = {
    "Podocyte": (["NPHS1"] * 15, ["NPHS1"] * 5),
    "Endothelial": (["PECAM1"] * 15, ["PECAM1"] * 5),
    "Mesangial": (["PDGFRB"] * 15, ["PDGFRB"] * 5),
    "PT": (["LRP2"] * 8 + ["CUBN"] * 7, ["LRP2"] * 3 + ["CUBN"] * 2),
    "TAL": (["UMOD"] * 15, ["UMOD"] * 5),
    "T cell": (["CD3D"] * 15, ["CD3D"] * 5),
}
ADMIXED_CELL, ADMIXED_TOWARD = "C03", "C06"
DEFAULT_RULE, ALTERNATIVE_RULE = "synthetic-by-construction", "synthetic-alternative"
ALTERNATIVE_LABELS = {"C06": "Podocyte"}  # the one cell whose label differs under the alternative rule
ADMIXED_EXPANSION_GENES = ["NPHS1", "LRP2", "LRP2", "LRP2", "LRP2"]
N_UNASSIGNED = 60
PANEL = sorted({gene for nuclear, expansion in GENES.values() for gene in nuclear + expansion})


def main() -> None:
    rng = np.random.default_rng(SEED)
    centres = {cid: (x, y, r) for cid, _, x, y, r in CELLS}
    rows: list[dict] = []
    for cell_id, cell_type, x, y, r in CELLS:
        nuclear_genes, expansion_genes = GENES[cell_type]
        for gene in nuclear_genes:
            d, angle = r * 0.9 * math.sqrt(rng.uniform()), rng.uniform(0, 2 * math.pi)
            rows.append(_molecule(gene, x, y, d, angle, cell_id, nuclear=True, nucleus_distance=0.0, rng=rng))
        if cell_id == ADMIXED_CELL:
            tx, ty, _ = centres[ADMIXED_TOWARD]
            facing = math.atan2(ty - y, tx - x)
            for i, gene in enumerate(ADMIXED_EXPANSION_GENES):
                d = rng.uniform(r + 0.5, r + EXPANSION_UM - 0.5)
                angle = facing + rng.uniform(-0.4, 0.4) if gene == "LRP2" else facing + math.pi
                rows.append(_molecule(gene, x, y, d, angle, cell_id, nuclear=False, nucleus_distance=d - r, rng=rng))
        else:
            for gene in expansion_genes:
                d, angle = rng.uniform(r + 0.5, r + EXPANSION_UM - 0.5), rng.uniform(0, 2 * math.pi)
                rows.append(_molecule(gene, x, y, d, angle, cell_id, nuclear=False, nucleus_distance=d - r, rng=rng))
    for i in range(N_UNASSIGNED):
        px, py = _point_outside_cells(rng, centres)
        nearest_edge = min(math.hypot(px - cx, py - cy) - cr for cx, cy, cr in centres.values())
        rows.append({"gene": PANEL[i % len(PANEL)], "x": px, "y": py, "cell_id": "", "overlaps_nucleus": 0,
                     "nucleus_distance": nearest_edge, "qv": rng.uniform(20, 40)})
    molecules = pd.DataFrame(rows)
    molecules.insert(0, "molecule_id", [f"{SECTION_ID}-m{i:04d}" for i in range(1, len(molecules) + 1)])
    cells = pd.DataFrame([
        {"cell_id": cid, "cell_type": ct, "cell_type_alternative": ALTERNATIVE_LABELS.get(cid, ct), "x": x, "y": y, "nucleus_area": math.pi * r**2, "cell_area": math.pi * (r + EXPANSION_UM) ** 2}
        for cid, ct, x, y, r in CELLS
    ])
    section_dir = OUT / SECTION_ID
    section_dir.mkdir(parents=True, exist_ok=True)
    molecules.to_csv(section_dir / "molecules.csv", index=False, float_format="%.3f")
    cells.to_csv(section_dir / "cells.csv", index=False, float_format="%.3f")
    (section_dir / "structures.json").write_text(json.dumps([_glomerulus()], indent=1) + "\n")
    (OUT / "dataset.json").write_text(json.dumps(_dataset_info(), indent=1) + "\n")
    print(f"wrote {len(molecules)} molecules, {len(cells)} cells and 1 glomerulus outline to {section_dir}")


def _molecule(gene, x, y, d, angle, cell_id, *, nuclear, nucleus_distance, rng) -> dict:
    return {"gene": gene, "x": x + d * math.cos(angle), "y": y + d * math.sin(angle), "cell_id": cell_id,
            "overlaps_nucleus": int(nuclear), "nucleus_distance": nucleus_distance, "qv": rng.uniform(20, 40)}


def _point_outside_cells(rng, centres) -> tuple[float, float]:
    x0, y0, x1, y1 = EXTENT
    while True:
        px, py = rng.uniform(x0 + 2, x1 - 2), rng.uniform(y0 + 2, y1 - 2)
        if all(math.hypot(px - cx, py - cy) > cr + EXPANSION_UM + 2 for cx, cy, cr in centres.values()):
            return px, py


def _glomerulus() -> dict:
    cx, cy = GLOMERULUS_CENTRE
    outline = []
    for k in range(48):
        theta = 2 * math.pi * k / 48
        radius = 33.0 + 1.5 * math.sin(3 * theta)
        outline.append([round(cx + radius * math.cos(theta), 3), round(cy + radius * math.sin(theta), 3)])
    return {"schema_version": "1.0", "structure_id": f"{SECTION_ID}-glomerulus-1", "section_id": SECTION_ID,
            "kind": "glomerulus", "outline": outline, "source": "synthetic"}


def _dataset_info() -> dict:
    return {
        "dataset_id": DATASET_ID,
        "title": "Synthetic kidney section (answers known by construction)",
        "description": "A hand-designed section for tests and the walking skeleton. Not real tissue; never cite it as a result.",
        "coordinate_units": "micrometre",
        "label_rule_id": DEFAULT_RULE,
        "label_rules": {DEFAULT_RULE: "cell_type", ALTERNATIVE_RULE: "cell_type_alternative"},
        "panel": PANEL,
        "sections": [{"section_id": SECTION_ID, "group": "Synthetic", "extent": EXTENT}],
        "capabilities": [
            {"capability": "coordinate_inspection", "status": "supported",
             "reason": "Molecule and cell positions are given in micrometres."},
            {"capability": "assignment_audit", "status": "supported",
             "reason": "Molecules carry cell_id and overlaps_nucleus, so default and nucleus-only conditions can be compared."},
            {"capability": "structure_outlines", "status": "supported",
             "reason": "One glomerulus outline is drawn by construction (not by SAM 3.1)."},
            {"capability": "disease_contrast", "status": "unavailable",
             "reason": "One synthetic section with no disease or control group, so no finding can be estimated."},
            {"capability": "cell_boundaries", "status": "unavailable",
             "reason": "No cell or nucleus boundaries; the viewer draws nuclei as circles from nucleus area, an approximation."},
        ],
    }


if __name__ == "__main__":
    main()
