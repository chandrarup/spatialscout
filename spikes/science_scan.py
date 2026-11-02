"""Scan every (cell type, gene) for DKD-vs-Control effects under each assignment condition, with count gates.
Spike code. Usage: python -I spikes/science_scan.py spikes/out/science_spike.pseudobulk.csv"""
import sys
import numpy as np
import pandas as pd

pb = pd.read_csv(sys.argv[1])
meta = {"n", "section", "group", "condition", "cell_type", "n_cells", "total"}
genes = [c for c in pb.columns if c not in meta]
rows = []
for ct, g_ct in pb.groupby("cell_type"):
    for gene in genes:
        eff, ok = {}, True
        d = g_ct[g_ct.condition == "default"]
        if d[gene].min() < 10 or (d.n_cells < 20).any():   # count gate: every section needs >= 10 molecules and >= 20 cells
            ok = False
        for cond, g in g_ct.groupby("condition"):
            v = np.log2(g[gene] / g.total.clip(lower=1) * 1e4 + 1)
            eff[cond] = v[g.group == "DKD"].mean() - v[g.group == "Control"].mean()
            if cond == "default":  # leave-one-section-out direction stability
                signs = []
                for drop in g.section:
                    k = g.section != drop
                    vv = v[k]; gg = g.group[k]
                    signs.append(np.sign(vv[gg == "DKD"].mean() - vv[gg == "Control"].mean()))
                loso = all(s_ == np.sign(eff["default"]) for s_ in signs)
        rng = max(eff.values()) - min(eff.values())
        flip = np.sign(eff["default"]) != np.sign(eff["nucleus_only"]) and abs(eff["default"]) > 0.2 and abs(eff["nucleus_only"]) > 0.2
        label = "insufficient" if not ok or not loso else ("sensitive" if (rng > 0.5 or flip) else "stable")
        rows.append(dict(cell_type=ct, gene=gene, label=label, default=eff["default"], nucleus_only=eff["nucleus_only"],
                         cap_1um=eff["cap_1um"], cap_2um=eff["cap_2um"], range=rng, flip=flip, loso=loso,
                         min_count_default=int(d[gene].min()), min_cells=int(d.n_cells.min())))
r = pd.DataFrame(rows)
pd.set_option("display.width", 200)
print(r.label.value_counts().to_string(), "\n")
print("=== label counts by cell type"); print(pd.crosstab(r.cell_type, r.label).to_string(), "\n")
fmt = lambda df: df[["cell_type", "gene", "label", "default", "nucleus_only", "cap_1um", "range", "flip", "loso", "min_count_default", "min_cells"]].round(2).to_string(index=False)
print("=== SENSITIVE (adequate counts, LOSO-stable under default), by |default effect|")
print(fmt(r[r.label == "sensitive"].assign(a=lambda x: x.default.abs()).sort_values("a", ascending=False).head(25)))
print("\n=== STABLE, largest |default effect|")
print(fmt(r[r.label == "stable"].assign(a=lambda x: x.default.abs()).sort_values("a", ascending=False).head(15)))
r.to_csv(sys.argv[1].replace(".pseudobulk.csv", ".scan.csv"), index=False)
