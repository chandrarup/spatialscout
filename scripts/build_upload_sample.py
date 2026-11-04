"""Build the upload sample: three 2 mm crops of GSE286184 sections, written back in Xenium's own output format
(`transcripts.parquet` and `cells.csv.gz`), so "Bring your own sections" can be tried without a download. Each crop is
centred on the window with the most podocytes under the full-panel rule. From the validated tables (`make data`).

    uv run python scripts/build_upload_sample.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SECTIONS = ("GSM8720409", "GSM8720410", "GSM8720411")
HALF = 1000.0
OUT = ROOT / "fixtures" / "upload_sample"


def main() -> None:
    for sid in SECTIONS:
        d = ROOT / "data" / "processed" / "GSE286184" / sid
        m = pd.read_parquet(d / "molecules.parquet")
        c = pd.read_parquet(d / "cells.parquet")
        pod = c[c["label:full-panel-v1"] == "Podocyte"]
        grid = pod.assign(gx=(pod.x // HALF).astype(int), gy=(pod.y // HALF).astype(int)).groupby(["gx", "gy"]).size().idxmax()
        cx, cy = (grid[0] + 0.5) * HALF, (grid[1] + 0.5) * HALF
        inside = lambda x, y: (x >= cx - HALF) & (x < cx + HALF) & (y >= cy - HALF) & (y < cy + HALF)  # noqa: E731
        mm = m[inside(m.x, m.y)]
        cc = c[inside(c.x, c.y)]
        out = OUT / sid
        out.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({
            "transcript_id": np.arange(len(mm), dtype=np.int64),
            "cell_id": mm["cell_id"].fillna("UNASSIGNED").astype(str).to_numpy(),
            "overlaps_nucleus": mm["overlaps_nucleus"].astype(int).to_numpy(),
            "feature_name": mm["gene"].astype(str).to_numpy(),
            "x_location": mm["x"].to_numpy(), "y_location": mm["y"].to_numpy(),
            "qv": mm["qv"].to_numpy(), "nucleus_distance": mm["nucleus_distance"].to_numpy(),
        }).to_parquet(out / "transcripts.parquet", index=False)
        pd.DataFrame({"cell_id": cc.cell_id.astype(str), "x_centroid": cc.x, "y_centroid": cc.y,
                      "nucleus_area": cc.nucleus_area, "cell_area": cc.cell_area}).to_csv(out / "cells.csv.gz", index=False)
        print(sid, len(mm), "molecules", len(cc), "cells", len(pod[inside(pod.x, pod.y)]), "podocytes")


if __name__ == "__main__":
    main()
