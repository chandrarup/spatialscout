"""Freeze exclusive marker pairs for the co-expression score from the single-nucleus reference (GSE271188 controls).

A pair (g, h) of markers for different compartments qualifies when, in every reference donor, nuclei detecting both
are under 1% of nuclei detecting either, and at least 300 nuclei detect either. The output is written once, before any
Xenium evaluation, and committed as configuration. Re-running reproduces it from the same inputs.

Usage: python -I spikes/freeze_marker_pairs.py <data/raw/GSE271188> <configs/exclusive_marker_pairs.json>
"""

import gzip
import hashlib
import itertools
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT, OUT = Path(sys.argv[1]), Path(sys.argv[2])
DONORS = {"GSM8371526": 14, "GSM8371535": 23}  # both "diagnosis: Control" in GEO
COMPARTMENT = {"NPHS1": "Podocyte", "ALDH1A2": "PEC", "LRP2": "PT", "CUBN": "PT", "UMOD": "TAL", "SLC12A3": "DCT",
               "AQP2": "PC", "SLC4A1": "IC", "PECAM1": "Endothelial", "PDGFRB": "Mesangial/Pericyte", "COL1A1": "Fibroblast",
               "CD3D": "T cell", "CD8A": "T cell", "MS4A1": "B cell", "CD68": "Myeloid", "ITGAX": "Myeloid"}
MAX_RATE, MIN_EITHER = 0.01, 300


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def detection(gsm, n):
    """Boolean nuclei x marker-gene detection matrix (count > 0) from a 10x MatrixMarket triplet file."""
    d = ROOT / gsm
    feats = pd.read_csv(d / f"{gsm}_kidney_snRNA_{n}_features.tsv.gz", sep="\t", header=None)
    row_of = {i + 1: sym for i, sym in enumerate(feats[1]) if sym in COMPARTMENT}  # MatrixMarket rows are 1-based
    mtx = d / f"{gsm}_kidney_snRNA_{n}_matrix.mtx.gz"
    with gzip.open(mtx, "rt") as fh:
        line = fh.readline()
        while line.startswith("%"):
            line = fh.readline()
        n_feat, n_cells, _ = (int(v) for v in line.split())
        hits = []
        for chunk in pd.read_csv(fh, sep=" ", header=None, names=["row", "col", "val"], chunksize=5_000_000):
            hits.append(chunk[chunk.row.isin(row_of.keys()) & (chunk.val > 0)])
    hits = pd.concat(hits)
    genes = sorted(set(row_of.values()))
    det = np.zeros((n_cells, len(genes)), dtype=bool)
    gi = {g: j for j, g in enumerate(genes)}
    det[hits.col.to_numpy() - 1, [gi[row_of[r]] for r in hits.row]] = True
    return genes, det, {"features": sha256(d / f"{gsm}_kidney_snRNA_{n}_features.tsv.gz"), "matrix": sha256(mtx)}, n_cells


per_donor, checksums, nuclei = {}, {}, {}
for gsm, n in DONORS.items():
    genes, det, sums, n_cells = detection(gsm, n)
    checksums[gsm], nuclei[gsm] = sums, n_cells
    gi = {g: j for j, g in enumerate(genes)}
    for g, h in itertools.combinations(sorted(COMPARTMENT), 2):
        if COMPARTMENT[g] == COMPARTMENT[h] or g not in gi or h not in gi:
            continue
        a, b = det[:, gi[g]], det[:, gi[h]]
        both, either = int((a & b).sum()), int((a | b).sum())
        per_donor.setdefault((g, h), {})[gsm] = {"both": both, "either": either, "rate": round(both / either, 5) if either else None}
    print(f"{gsm}: {n_cells} nuclei, {len(genes)} marker genes found", flush=True)

pairs, rejected = [], []
for (g, h), by in sorted(per_donor.items()):
    ok = len(by) == len(DONORS) and all(v["either"] >= MIN_EITHER and v["rate"] is not None and v["rate"] < MAX_RATE for v in by.values())
    rec = {"genes": [g, h], "compartments": [COMPARTMENT[g], COMPARTMENT[h]], "per_donor": by}
    (pairs if ok else rejected).append(rec)

out = {
    "schema_version": "1.0",
    "artifact": "exclusive_marker_pairs",
    "frozen_on": date.today().isoformat(),
    "source": {"dataset": "GSE271188", "url": "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE271188",
               "donors": {gsm: {"section_name": f"kidney_snRNA_{n}", "diagnosis": "Control", "nuclei": nuclei[gsm], "sha256": checksums[gsm]}
                          for gsm, n in DONORS.items()}},
    "rule": {"max_codetection_rate": MAX_RATE, "min_nuclei_detecting_either": MIN_EITHER, "applies_to": "every donor",
             "definition": "rate = nuclei detecting both / nuclei detecting either (count > 0)"},
    "compartment_of": COMPARTMENT,
    "pairs": pairs,
    "rejected": rejected,
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, indent=1) + "\n")
print(f"{len(pairs)} pairs frozen, {len(rejected)} rejected -> {OUT}")
for p in pairs:
    print("  ", p["genes"], {k: v["rate"] for k, v in p["per_donor"].items()})
