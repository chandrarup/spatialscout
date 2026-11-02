"""Science spike: does podocyte LRP2/CUBN co-expression survive stricter transcript assignment?

Throwaway exploration code, not the product. Reads GSE286184 Xenium sections (paths passed in),
annotates cells once from default counts with a panel-marker rule, freezes those labels, then compares
assignment conditions. Every number is reported beside molecule retention.

Usage: python -I spikes/science_spike.py <data/raw/GSE286184> <out.json>
"""

import gzip
import io
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT, OUT = Path(sys.argv[1]), Path(sys.argv[2])
GROUPS = {1: "Control", 2: "Control", 6: "Control", 3: "DKD", 4: "DKD", 5: "DKD", 7: "DKD", 8: "DKD", 9: "DKD"}

# Panel-marker rule. One or two specific markers per compartment, chosen from the 50-gene panel before looking at results.
MARKERS = {
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
DE_GENES = ["NPHS1", "LRP2", "CUBN", "VCAM1", "PTPRC", "CD3D", "CD68", "UMOD", "POSTN", "COL1A1", "PECAM1", "PDGFRB", "STAT1", "HLA-DRA"]
DE_TYPES = ["Podocyte", "PT", "Endothelial"]
CAPS_UM = [1.0, 2.0]


def load(n):
    gsm = f"GSM{8720408 + n}"
    d = ROOT / gsm
    feats = pd.read_csv(d / f"{gsm}_kidney_xenium_{n}_features.tsv.gz", sep="\t", header=None)
    panel = set(feats.loc[feats[2] == "Gene Expression", 1])
    with gzip.open(d / f"{gsm}_kidney_xenium_{n}_transcripts.parquet.gz") as fh:
        raw = io.BytesIO(fh.read())
    tx = pd.read_parquet(raw,
                         columns=["cell_id", "overlaps_nucleus", "feature_name", "x_location", "y_location", "qv", "nucleus_distance"])
    tx = tx[(tx.qv >= 20) & tx.feature_name.isin(panel)]
    cells = pd.read_csv(d / f"{gsm}_kidney_xenium_{n}_cells.csv.gz")
    return gsm, panel, tx, cells


def annotate(assigned, gene_scale):
    counts = assigned.groupby(["cell_id", "feature_name"]).size().unstack(fill_value=0)
    norm = counts.div(pd.Series(gene_scale)[counts.columns], axis=1)
    scores = pd.DataFrame({t: norm[[g for g in gs if g in norm]].max(axis=1) for t, gs in MARKERS.items()})
    label = scores.idxmax(axis=1).where(scores.max(axis=1) >= 0.5, "Unlabelled")
    label[counts.sum(axis=1) < 5] = "Low quality"
    return label


def condition_masks(assigned):
    m = {"default": np.ones(len(assigned), bool), "nucleus_only": (assigned.overlaps_nucleus == 1).to_numpy()}
    for c in CAPS_UM:
        m[f"cap_{c:g}um"] = (assigned.nucleus_distance <= c).to_numpy() | m["nucleus_only"]
    return m


# Gene scale: typical count of a gene in cells that express it, pooled over control sections (frozen before annotation).
sections = {n: load(n) for n in sorted(GROUPS)}
pool = pd.concat([s[2][s[2].cell_id != "UNASSIGNED"] for n, s in sections.items() if GROUPS[n] == "Control"])
pc = pool.groupby(["cell_id", "feature_name"]).size()
gene_scale = pc.groupby(level="feature_name").mean().to_dict()

report = {"sections": {}, "pseudobulk": {}}
pb_rows = []
for n, (gsm, panel, tx, cells) in sections.items():
    assigned = tx[tx.cell_id != "UNASSIGNED"].copy()
    labels = annotate(assigned, gene_scale)
    assigned["cell_type"] = assigned.cell_id.map(labels)
    masks = condition_masks(assigned)
    sec = {"group": GROUPS[n], "n_transcripts_qv20_panel": int(len(tx)), "n_assigned": int(len(assigned)),
           "unassigned_frac": round(1 - len(assigned) / len(tx), 4),
           "cell_type_counts": labels.value_counts().to_dict(), "conditions": {}}
    pod = assigned.cell_type == "Podocyte"
    for cname, mk in masks.items():
        a = assigned[mk]
        pod_cells = labels.index[labels == "Podocyte"]
        pc_counts = a[a.cell_type == "Podocyte"].groupby(["cell_id", "feature_name"]).size().unstack(fill_value=0).reindex(pod_cells, fill_value=0)
        get = lambda g: pc_counts[g] if g in pc_counts else pd.Series(0, index=pc_counts.index)
        sec["conditions"][cname] = {
            "retention_all": round(mk.mean(), 4),
            "retention_podocyte_NPHS1": round(mk[pod & (assigned.feature_name == "NPHS1").to_numpy()].mean(), 4),
            "retention_podocyte_LRP2": round(mk[pod & (assigned.feature_name == "LRP2").to_numpy()].mean(), 4) if (pod & (assigned.feature_name == "LRP2")).any() else None,
            "retention_podocyte_CUBN": round(mk[pod & (assigned.feature_name == "CUBN").to_numpy()].mean(), 4) if (pod & (assigned.feature_name == "CUBN")).any() else None,
            "podocytes": int(len(pod_cells)),
            "frac_podocytes_LRP2_pos": round((get("LRP2") > 0).mean(), 4),
            "frac_podocytes_CUBN_pos": round((get("CUBN") > 0).mean(), 4),
            "frac_podocytes_LRP2_or_CUBN_pos": round(((get("LRP2") > 0) | (get("CUBN") > 0)).mean(), 4),
            "mean_LRP2_per_podocyte": round(get("LRP2").mean(), 4),
            "mean_NPHS1_per_podocyte": round(get("NPHS1").mean(), 4),
        }
        for ct in list(MARKERS):
            sub = a[a.cell_type == ct]
            gc = sub.feature_name.value_counts()
            pb_rows.append({"section": gsm, "n": n, "group": GROUPS[n], "condition": cname, "cell_type": ct,
                            "n_cells": int((labels == ct).sum()), "total": int(len(sub)), **{g: int(gc.get(g, 0)) for g in sorted(panel)}})
    # Nuclear fraction: what share of a gene's molecules in a cell type overlap the nucleus?
    nf = {}
    for ct, g in [("PT", "LRP2"), ("Podocyte", "LRP2"), ("PT", "CUBN"), ("Podocyte", "CUBN"), ("Podocyte", "NPHS1"), ("TAL", "UMOD"), ("Podocyte", "UMOD")]:
        s = assigned[(assigned.cell_type == ct) & (assigned.feature_name == g)]
        nf[f"{g}|{ct}"] = {"n": int(len(s)), "nuclear_frac": round(s.overlaps_nucleus.mean(), 4) if len(s) else None,
                           "median_nucleus_distance": round(s.nucleus_distance.median(), 3) if len(s) else None}
    sec["nuclear_fraction"] = nf
    sec["nucleus_distance_quantiles_nonnuclear"] = assigned.loc[assigned.overlaps_nucleus == 0, "nucleus_distance"].quantile([.25, .5, .75, .9]).round(2).to_dict()
    report["sections"][gsm] = sec
    print(f"{gsm} x{n} {GROUPS[n]}: {len(assigned)} assigned, podocytes={sec['conditions']['default']['podocytes']}", flush=True)

pb = pd.DataFrame(pb_rows)
for (cname, ct), g in pb[pb.cell_type.isin(DE_TYPES)].groupby(["condition", "cell_type"]):
    res = {}
    for gene in DE_GENES:
        cpm = np.log2(g[gene] / g["total"].clip(lower=1) * 1e4 + 1)
        dkd, ctl = cpm[g.group == "DKD"], cpm[g.group == "Control"]
        res[gene] = {"log2fc": round(dkd.mean() - ctl.mean(), 3), "welch_p": round(float(stats.ttest_ind(dkd, ctl, equal_var=False).pvalue), 4),
                     "per_section_log2cp10k": {s: round(v, 3) for s, v in zip(g.section, cpm)}}
    report["pseudobulk"][f"{cname}|{ct}"] = res
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(report, indent=1, default=float))
pb.to_csv(OUT.with_suffix(".pseudobulk.csv"), index=False)

# Compact summary
print("\n=== Podocyte LRP2/CUBN co-expression by condition (mean over sections; retention beside it)")
for cname in next(iter(report["sections"].values()))["conditions"]:
    rows = [s["conditions"][cname] for s in report["sections"].values()]
    f = lambda k: np.nanmean([r[k] for r in rows if r[k] is not None])
    print(f"  {cname:13s} retention_all={f('retention_all'):.3f} | pod NPHS1 kept={f('retention_podocyte_NPHS1'):.3f} LRP2 kept={f('retention_podocyte_LRP2'):.3f} CUBN kept={f('retention_podocyte_CUBN'):.3f}"
          f" | pods LRP2+={f('frac_podocytes_LRP2_pos'):.3f} CUBN+={f('frac_podocytes_CUBN_pos'):.3f} either={f('frac_podocytes_LRP2_or_CUBN_pos'):.3f}")
print("\n=== Nuclear fraction of molecules (pooled mean over sections)")
for k in next(iter(report["sections"].values()))["nuclear_fraction"]:
    vals = [s["nuclear_fraction"][k]["nuclear_frac"] for s in report["sections"].values() if s["nuclear_fraction"][k]["nuclear_frac"] is not None]
    d = [s["nuclear_fraction"][k]["median_nucleus_distance"] for s in report["sections"].values() if s["nuclear_fraction"][k]["median_nucleus_distance"] is not None]
    print(f"  {k:16s} nuclear_frac={np.mean(vals):.3f} (range {min(vals):.3f}-{max(vals):.3f})  median nucleus_distance={np.mean(d):.2f} um")
print("\n=== DKD vs Control pseudobulk log2FC by condition (Podocyte)")
conds = sorted({k.split('|')[0] for k in report['pseudobulk']})
for gene in DE_GENES:
    vals = {c: report["pseudobulk"][f"{c}|Podocyte"][gene]["log2fc"] for c in conds}
    ps = {c: report["pseudobulk"][f"{c}|Podocyte"][gene]["welch_p"] for c in conds}
    rng = max(vals.values()) - min(vals.values())
    print(f"  {gene:8s} " + "  ".join(f"{c}={vals[c]:+.2f}(p={ps[c]:.3f})" for c in conds) + f"  | range={rng:.2f}{'  SENSITIVE' if rng > 0.5 else ''}")
