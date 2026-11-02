"""SAM spike 3: NPHS1-cluster boxes -> SAM 3.1 box prompts on the gene-agnostic nucleus rendering.

Spike code. NPHS1 seeds the boxes, so NPHS1 cannot validate the masks. Validation uses glomerular tuft genes the seeding
never saw (PECAM1 endothelium, PDGFRB mesangium), comparing SAM masks with the seed boxes themselves.
Usage: python -I spikes/sam_spike3.py <section_dir> <section_n> <.env> <spike1_out_dir>
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
from meta_sam_parser import (FramePrompt, PromptBox, PromptObject, build_object_prompt, decode_mask_to_raster,
                             image_segmentation_format, parse_responses_stream)
from openai import AsyncOpenAI
from PIL import Image, ImageDraw, ImageFilter
from sklearn.cluster import DBSCAN

SEC, N, ENV, OUT = Path(sys.argv[1]), int(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
env = dict(l.strip().split("=", 1) for l in ENV.read_text().splitlines() if "=" in l)
meta = json.loads((OUT / "sam_spike.json").read_text()); x0, y0 = meta["crop_origin_um"]; C = meta["crop_um"]; W = H = int(C)
png = (OUT / "nucleus_discs.png").read_bytes(); url = "data:image/png;base64," + base64.b64encode(png).decode()
with gzip.open(SEC / f"{SEC.name}_kidney_xenium_{N}_transcripts.parquet.gz") as fh:
    tx = pd.read_parquet(io.BytesIO(fh.read()), columns=["feature_name", "x_location", "y_location", "qv"])
tx = tx[(tx.qv >= 20) & tx.x_location.between(x0, x0 + C - 1e-6) & tx.y_location.between(y0, y0 + C - 1e-6)]
pix = lambda g: (np.clip(g.x_location.to_numpy() - x0, 0, W - 1).astype(int), np.clip(g.y_location.to_numpy() - y0, 0, H - 1).astype(int))

nphs1 = tx[tx.feature_name == "NPHS1"]
lab = DBSCAN(eps=25, min_samples=12).fit_predict(nphs1[["x_location", "y_location"]].to_numpy())
boxes = []
for k in sorted(set(lab) - {-1}):
    c = nphs1[lab == k]
    l, t, r, b = c.x_location.min() - x0 - 15, c.y_location.min() - y0 - 15, c.x_location.max() - x0 + 15, c.y_location.max() - y0 + 15
    boxes.append(tuple(int(v) for v in (max(0, l), max(0, t), min(W, r), min(H, b))))
print(f"{len(boxes)} NPHS1 clusters -> boxes {boxes}", flush=True)


def enrich(mask, gene):
    xs, ys = pix(tx[tx.feature_name == gene]); inn = mask[ys, xs].sum()
    return round(float((inn / max(mask.sum(), 1)) / max((len(xs) - inn) / max((~mask).sum(), 1), 1e-9)), 2), round(float(inn / max(len(xs), 1)), 3)


def report(name, mask):
    out = {"area_frac": round(float(mask.mean()), 4)}
    for g in ["PECAM1", "PDGFRB", "NPHS1", "UMOD", "LRP2"]:
        out[g] = dict(zip(["enrichment", "frac_inside"], enrich(mask, g)))
    print(f"  {name:22s} area={out['area_frac']:.3f} " + " ".join(f"{g}:x{v['enrichment']}({v['frac_inside']:.0%})" for g, v in out.items() if g != "area_frac"), flush=True)
    return out


async def main():
    box_mask = np.zeros((H, W), bool)
    for l, t, r, b in boxes:
        box_mask[t:b, l:r] = True
    res_box = report("seed boxes", box_mask)
    prompt = build_object_prompt(size=(W, H), objects=[PromptObject(id=i + 1, prompts=[FramePrompt(box=PromptBox(left=l, top=t, right=r, bottom=b))]) for i, (l, t, r, b) in enumerate(boxes[:16])])
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
                yield {"type": "response.output_text.done", "item_id": data.get("item_id"), "output_index": data.get("output_index"), "content_index": data.get("content_index"), "text": part["text"]}

    t0 = time.time()
    async with AsyncOpenAI(base_url="https://api.meta.ai/v1", api_key=env["META_API_KEY"]) as api:
        stream = await api.responses.create(model="sam-3.1", stream=True, input=[{"type": "message", "role": "user", "content": [{"type": "input_text", "text": prompt}, {"type": "input_image", "image_url": url}]}])
        async with stream, aclosing(events(stream)) as evs:
            res = await parse_responses_stream(evs, image_segmentation_format()).final_result()
    rb = {r.object_id: r for r in res.records if r.kind == "box"}
    mask = np.zeros((H, W), bool); areas = []
    for rec in (r for r in res.records if r.kind == "mask"):
        b, m = rb[rec.object_id], rec.mask
        local = np.frombuffer(decode_mask_to_raster(m), dtype=np.uint8).reshape(m.height, m.width).astype(bool)
        mask[b.top:b.top + m.height, b.left:b.left + m.width] |= local; areas.append(int(local.sum()))
    print(f"SAM 3.1: {len(areas)} masks in {time.time()-t0:.1f}s, areas um2={areas}", flush=True)
    res_sam = report("SAM 3.1 masks", mask)
    img = Image.open(io.BytesIO(png)).convert("RGB"); d = ImageDraw.Draw(img)
    for l, t, r, b in boxes:
        d.rectangle([l, t, r, b], outline=(255, 120, 0), width=2)
    arr = np.asarray(img).copy()
    edge = mask ^ np.asarray(Image.fromarray(mask.astype(np.uint8) * 255).filter(ImageFilter.MinFilter(5))).astype(bool)
    arr[edge] = [0, 200, 255]
    xs, ys = pix(nphs1); arr[ys, xs] = [230, 180, 0]
    Image.fromarray(arr).save(OUT / "overlay_nphs1boxes_sam_masks.png")
    (OUT / "sam_spike3.json").write_text(json.dumps({"boxes": boxes, "seed_boxes": res_box, "sam_masks": res_sam, "areas": areas}, indent=1))


asyncio.run(main())
