"""Spike helper: draw NPHS1 molecules (yellow) over the nucleus-disc rendering to see where glomeruli are."""
import gzip, io, json, sys
from pathlib import Path
import numpy as np, pandas as pd
from PIL import Image, ImageDraw
SEC, N, OUT = Path(sys.argv[1]), int(sys.argv[2]), Path(sys.argv[3])
meta = json.loads((OUT / "sam_spike.json").read_text()); x0, y0 = meta["crop_origin_um"]; C = meta["crop_um"]
with gzip.open(SEC / f"{SEC.name}_kidney_xenium_{N}_transcripts.parquet.gz") as fh:
    tx = pd.read_parquet(io.BytesIO(fh.read()), columns=["feature_name", "x_location", "y_location", "qv"])
img = Image.open(OUT / "nucleus_discs.png").convert("RGB"); d = ImageDraw.Draw(img)
for gene, col in [("NPHS1", (255, 200, 0)), ("PECAM1", (0, 170, 0))]:
    g = tx[(tx.qv >= 20) & (tx.feature_name == gene) & tx.x_location.between(x0, x0 + C) & tx.y_location.between(y0, y0 + C)]
    for x, y in zip(g.x_location - x0, g.y_location - y0):
        d.ellipse([x - 2.5, y - 2.5, x + 2.5, y + 2.5], fill=col)
img.save(OUT / "nphs1_pecam1_on_discs.png")
