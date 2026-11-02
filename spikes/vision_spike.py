"""Vision spike: does muse-spark-1.3 read a per-section plot correctly and catch a planted plot-claim mismatch?

Spike code. Uses real per-section pseudobulk values from the science spike (C3 in proximal-tubule cells, default condition).
Usage: python -I spikes/vision_spike.py <science_spike.pseudobulk.csv> <.env> <out_dir>
"""

import base64
import io
import json
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from openai import OpenAI

PB, ENV, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
env = dict(l.strip().split("=", 1) for l in ENV.read_text().splitlines() if "=" in l)
GENE, CT = "C3", "PT"
pb = pd.read_csv(PB)
d = pb[(pb.cell_type == CT) & (pb.condition == "default")].copy()
d["v"] = np.log2(d[GENE] / d.total * 1e4 + 1)
claim = {"claim_id": "spike-c3-pt", "text": f"{GENE} is higher in DKD than in Control in {CT} cells", "gene": GENE, "cell_type": CT,
         "direction": "higher_in_DKD", "log2fc": round(d[d.group == "DKD"].v.mean() - d[d.group == "Control"].v.mean(), 2),
         "n_sections": {"DKD": int((d.group == "DKD").sum()), "Control": int((d.group == "Control").sum())}}


def render(data, swap_labels=False, title_suffix=""):
    fig, ax = plt.subplots(figsize=(6, 5), dpi=150)
    groups = ["Control", "DKD"]
    for i, g in enumerate(groups):
        v = data[data.group == g].v.to_numpy()
        ax.scatter(np.full(len(v), i) + np.linspace(-0.12, 0.12, len(v)), v, s=70, color=["#4C9BE8", "#E8684C"][i], zorder=3)
        ax.hlines(v.mean(), i - 0.25, i + 0.25, color="black", lw=2)
    shown = [f"{g} (n={int((data.group == g).sum())})" for g in groups]
    if swap_labels:
        shown = shown[::-1]
    ax.set_xticks([0, 1], shown, fontsize=13)
    ax.set_ylabel(f"{GENE} log2(CP10K + 1) per section", fontsize=12)
    ax.set_title(f"{GENE} in {CT} cells, pseudobulk per section{title_suffix}", fontsize=13)
    ax.grid(axis="y", alpha=0.3)
    b = io.BytesIO(); fig.tight_layout(); fig.savefig(b, format="png"); plt.close(fig)
    return b.getvalue()


SCHEMA = {"type": "object", "additionalProperties": False,
          "required": ["higher_group_in_plot", "n_points_by_group", "single_point_driven", "direction_matches_claim", "counts_match_claim", "rationale"],
          "properties": {"higher_group_in_plot": {"type": "string", "enum": ["DKD", "Control", "unclear"]},
                         "n_points_by_group": {"type": "object", "additionalProperties": False, "required": ["DKD", "Control"],
                                               "properties": {"DKD": {"type": "integer"}, "Control": {"type": "integer"}}},
                         "single_point_driven": {"type": "boolean"}, "direction_matches_claim": {"type": "boolean"},
                         "counts_match_claim": {"type": "boolean"}, "rationale": {"type": "string"}}}
INSTR = ("You are a figure checker. Read ONLY the plot image: group labels on the x axis, the points, and the black mean bars. "
         "Do not trust the claim; compare it with what the plot shows. Claim JSON:\n")
client = OpenAI(base_url="https://api.meta.ai/v1", api_key=env["META_API_KEY"])
cases = {
    "correct": (render(d), {"direction_matches_claim": True, "counts_match_claim": True}),
    "swapped_labels": (render(d, swap_labels=True), {"direction_matches_claim": False}),
    "wrong_count": (render(d.drop(d[d.group == "DKD"].index[0])), {"counts_match_claim": False}),
}
results = {}
for name, (png, expect) in cases.items():
    (OUT / f"vision_{name}.png").write_bytes(png)
    t = time.time()
    r = client.chat.completions.create(model="muse-spark-1.3", reasoning_effort="low", max_completion_tokens=4000,
                                       response_format={"type": "json_schema", "json_schema": {"name": "PlotCheck", "strict": True, "schema": SCHEMA}},
                                       messages=[{"role": "user", "content": [{"type": "text", "text": INSTR + json.dumps(claim)},
                                                                              {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(png).decode()}}]}])
    v = json.loads(r.choices[0].message.content)
    ok = all(v[k] == want for k, want in expect.items())
    results[name] = {"verdict": v, "expected": expect, "pass": ok, "latency_s": round(time.time() - t, 1), "usage": r.usage.model_dump() if r.usage else None}
    print(f"{name:15s} {'PASS' if ok else 'FAIL'} in {results[name]['latency_s']}s: higher={v['higher_group_in_plot']} n={v['n_points_by_group']} "
          f"dir_ok={v['direction_matches_claim']} counts_ok={v['counts_match_claim']} single={v['single_point_driven']} | {v['rationale'][:160]}", flush=True)
(OUT / "vision_spike.json").write_text(json.dumps({"claim": claim, "results": results}, indent=1))
