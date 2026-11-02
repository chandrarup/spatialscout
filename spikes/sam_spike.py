"""SAM spike: can sam-3.1 find glomeruli in an image rendered from Xenium transcripts?

Spike code. The image is gene-agnostic (nucleus-overlapping molecules of every gene, or nucleus discs from the
cells table), so NPHS1 (podocyte) enrichment inside the returned masks is an independent check. NPHS1 is used only to
choose which crop to look at, never to draw the image or prompt SAM.

Usage: python -I spikes/sam_spike.py <section_dir> <section_n> <.env> <out_dir>
"""

import asyncio
import base64
import gzip
import io
import json
import sys
import time
from contextlib import aclosing
from pathlib import Path

import numpy as np
import pandas as pd
from meta_sam_parser import decode_mask_to_raster, image_segmentation_format, parse_responses_stream
from openai import AsyncOpenAI
from PIL import Image, ImageDraw, ImageFilter

SEC, N, ENV, OUT = Path(sys.argv[1]), int(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
OUT.mkdir(parents=True, exist_ok=True)
env = dict(l.strip().split("=", 1) for l in ENV.read_text().splitlines() if "=" in l)
gsm = SEC.name
with gzip.open(SEC / f"{gsm}_kidney_xenium_{N}_transcripts.parquet.gz") as fh:
    tx = pd.read_parquet(io.BytesIO(fh.read()), columns=["feature_name", "x_location", "y_location", "overlaps_nucleus", "qv"])
tx = tx[tx.qv >= 20]
cells = pd.read_csv(SEC / f"{gsm}_kidney_xenium_{N}_cells.csv.gz")

CROP = 1000.0  # um; 1 px = 1 um
nphs1 = tx[tx.feature_name == "NPHS1"]
H, xe, ye = np.histogram2d(nphs1.x_location, nphs1.y_location, bins=[np.arange(0, tx.x_location.max() + 100, 100), np.arange(0, tx.y_location.max() + 100, 100)])
k = int(CROP / 100)
best, bx, by = -1, 0, 0
for i in range(max(1, H.shape[0] - k + 1)):
    for j in range(max(1, H.shape[1] - k + 1)):
        s = H[i:i + k, j:j + k].sum()
        if s > best:
            best, bx, by = s, xe[i], ye[j]
x0, y0 = float(bx), float(by)
inside = lambda d: d[(d.x_location >= x0) & (d.x_location < x0 + CROP) & (d.y_location >= y0) & (d.y_location < y0 + CROP)]
crop_tx, crop_nphs1 = inside(tx), inside(nphs1)
print(f"crop origin=({x0:.0f},{y0:.0f}) um, {len(crop_tx)} molecules, {len(crop_nphs1)} NPHS1 in crop", flush=True)


def to_png(arr):
    b = io.BytesIO(); Image.fromarray(arr).save(b, "PNG"); return b.getvalue()


def render_nuclear_density():
    nuc = crop_tx[crop_tx.overlaps_nucleus == 1]
    h, _, _ = np.histogram2d(nuc.y_location - y0, nuc.x_location - x0, bins=[int(CROP), int(CROP)], range=[[0, CROP], [0, CROP]])
    img = Image.fromarray((255 * np.clip(np.log1p(h) / np.log1p(np.percentile(h[h > 0], 99)), 0, 1)).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5))
    a = np.asarray(img).astype(float) / 255
    rgb = np.stack([a * 120, a * 160, 40 + a * 215], -1).clip(0, 255).astype(np.uint8)  # DAPI-like blue on black
    return rgb


def render_nucleus_discs():
    c = cells[(cells.x_centroid >= x0) & (cells.x_centroid < x0 + CROP) & (cells.y_centroid >= y0) & (cells.y_centroid < y0 + CROP)]
    img = Image.new("RGB", (int(CROP), int(CROP)), (244, 226, 236))  # eosin-pink background
    d = ImageDraw.Draw(img)
    for _, r in c.iterrows():
        rad = max(1.5, float(np.sqrt(max(r.nucleus_area, 1) / np.pi)))
        cx, cy = r.x_centroid - x0, r.y_centroid - y0
        d.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=(72, 52, 140))  # hematoxylin purple
    return np.asarray(img.filter(ImageFilter.GaussianBlur(0.8)))


async def sam(png, prompt):
    url = "data:image/png;base64," + base64.b64encode(png).decode()
    done = set()

    async def events(stream):
        async for ev in stream:
            data = ev.model_dump() if hasattr(ev, "model_dump") else dict(ev)
            lane = (data.get("item_id"), data.get("output_index"), data.get("content_index"))
            if data.get("type") == "response.output_text.done":
                if lane not in done:
                    done.add(lane); yield data
                continue
            yield data
            part = data.get("part")
            if data.get("type") == "response.content_part.done" and lane not in done and isinstance(part, dict) and part.get("type") == "output_text":
                done.add(lane)
                yield {"type": "response.output_text.done", "item_id": data.get("item_id"), "output_index": data.get("output_index"),
                       "content_index": data.get("content_index"), "text": part["text"]}

    async with AsyncOpenAI(base_url="https://api.meta.ai/v1", api_key=env["META_API_KEY"]) as api:
        stream = await api.responses.create(model="sam-3.1", stream=True, metadata={"include_confidence": "true"},
                                            input=[{"type": "message", "role": "user", "content": [{"type": "input_text", "text": prompt}, {"type": "input_image", "image_url": url}]}])
        async with stream, aclosing(events(stream)) as evs:
            return await parse_responses_stream(evs, image_segmentation_format()).final_result()


def evaluate(res):
    mask = np.zeros((int(CROP), int(CROP)), bool)
    boxes = {r.object_id: r for r in res.records if r.kind == "box"}
    objs = []
    for r in (r for r in res.records if r.kind == "mask"):
        b, m = boxes[r.object_id], r.mask
        local = np.frombuffer(decode_mask_to_raster(m), dtype=np.uint8).reshape(m.height, m.width).astype(bool)
        mask[b.top:b.top + m.height, b.left:b.left + m.width] |= local
        objs.append({"id": r.object_id, "area_um2": int(local.sum()), "box": [b.left, b.top, b.right, b.bottom]})
    if not objs:
        return mask, {"n_objects": 0}
    px = np.clip(crop_nphs1.x_location.to_numpy() - x0, 0, CROP - 1).astype(int)
    py = np.clip(crop_nphs1.y_location.to_numpy() - y0, 0, CROP - 1).astype(int)
    in_n = mask[py, px].sum()
    area_in = mask.mean()
    dens_in = in_n / max(mask.sum(), 1)
    dens_out = (len(px) - in_n) / max((~mask).sum(), 1)
    return mask, {"n_objects": len(objs), "mask_area_frac": round(float(area_in), 4), "nphs1_frac_inside": round(float(in_n / max(len(px), 1)), 4),
                  "nphs1_enrichment_in_vs_out": round(float(dens_in / max(dens_out, 1e-9)), 2), "objects": objs}


async def main():
    images = {"nuclear_density": render_nuclear_density(), "nucleus_discs": render_nucleus_discs()}
    results = {}
    for iname, arr in images.items():
        Image.fromarray(arr).save(OUT / f"{iname}.png")
        for prompt in ["glomerulus", "round cluster of cells", "blob"]:
            t = time.time()
            try:
                res = await sam(to_png(arr), prompt)
            except Exception as e:  # spike: record and move on
                results[f"{iname}|{prompt}"] = {"error": repr(e)[:200]}; continue
            mask, ev = evaluate(res)
            ev["latency_s"] = round(time.time() - t, 1)
            results[f"{iname}|{prompt}"] = ev
            print(f"{iname:16s} {prompt!r:26s} -> {ev.get('n_objects')} objs, NPHS1 inside={ev.get('nphs1_frac_inside')}, "
                  f"enrichment={ev.get('nphs1_enrichment_in_vs_out')}, area_frac={ev.get('mask_area_frac')}, {ev['latency_s']}s", flush=True)
            if ev.get("n_objects"):
                ov = arr.copy(); edge = mask ^ np.asarray(Image.fromarray(mask.astype(np.uint8) * 255).filter(ImageFilter.MinFilter(5))).astype(bool)
                ov[edge] = [0, 255, 255]
                px = np.clip(crop_nphs1.x_location.to_numpy() - x0, 0, CROP - 1).astype(int); py = np.clip(crop_nphs1.y_location.to_numpy() - y0, 0, CROP - 1).astype(int)
                ov[py, px] = [255, 220, 0]
                Image.fromarray(ov).save(OUT / f"overlay_{iname}_{prompt.replace(' ', '_')}.png")
    (OUT / "sam_spike.json").write_text(json.dumps({"section": gsm, "crop_origin_um": [x0, y0], "crop_um": CROP, "results": results}, indent=1))


asyncio.run(main())
