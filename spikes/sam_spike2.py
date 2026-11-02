"""SAM spike 2: Spark 1.3 proposes glomerulus boxes on the RNA-derived image; SAM 3.1 delineates them from box prompts.

Spike code. Neither model sees NPHS1; NPHS1 enrichment inside the masks is the independent check.
Usage: python -I spikes/sam_spike2.py <section_dir> <section_n> <.env> <spike1_out_dir>
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

SEC, N, ENV, OUT = Path(sys.argv[1]), int(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
env = dict(l.strip().split("=", 1) for l in ENV.read_text().splitlines() if "=" in l)
meta = json.loads((OUT / "sam_spike.json").read_text())
x0, y0 = meta["crop_origin_um"]; CROP = meta["crop_um"]; W = H = int(CROP)
png = (OUT / "nucleus_discs.png").read_bytes()
url = "data:image/png;base64," + base64.b64encode(png).decode()
gsm = SEC.name
with gzip.open(SEC / f"{gsm}_kidney_xenium_{N}_transcripts.parquet.gz") as fh:
    tx = pd.read_parquet(io.BytesIO(fh.read()), columns=["feature_name", "x_location", "y_location", "qv"])
nphs1 = tx[(tx.qv >= 20) & (tx.feature_name == "NPHS1")]
nphs1 = nphs1[(nphs1.x_location >= x0) & (nphs1.x_location < x0 + CROP) & (nphs1.y_location >= y0) & (nphs1.y_location < y0 + CROP)]
px = np.clip(nphs1.x_location.to_numpy() - x0, 0, W - 1).astype(int); py = np.clip(nphs1.y_location.to_numpy() - y0, 0, H - 1).astype(int)

SCHEMA = {"type": "object", "additionalProperties": False, "required": ["glomeruli", "notes"], "properties": {
    "notes": {"type": "string"},
    "glomeruli": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["x1", "y1", "x2", "y2", "confidence"],
                                             "properties": {"x1": {"type": "integer"}, "y1": {"type": "integer"}, "x2": {"type": "integer"}, "y2": {"type": "integer"},
                                                            "confidence": {"type": "number"}}}}}}
PROMPT = ("This is a rendering of a human kidney biopsy section made from spatial transcriptomics data: each purple disc is one cell nucleus, "
          "drawn at its measured position and size, on a pink background. Scale: 1 pixel = 1 micrometre; the image is 1000 x 1000 pixels. "
          "Tubules appear as rings or chains of nuclei. Renal glomeruli appear as roughly round, densely packed clusters of many nuclei, "
          "typically 100-250 micrometres across. Return a bounding box for every glomerulus you can see, in coordinates on a 0-1000 grid "
          "(x to the right, y down). Return an empty list if there are none.")


def nphs1_eval(mask):
    inn = mask[py, px].sum()
    dens_in = inn / max(mask.sum(), 1); dens_out = (len(px) - inn) / max((~mask).sum(), 1)
    return {"nphs1_frac_inside": round(float(inn / max(len(px), 1)), 4), "area_frac": round(float(mask.mean()), 4),
            "nphs1_enrichment_in_vs_out": round(float(dens_in / max(dens_out, 1e-9)), 2)}


async def main():
    async with AsyncOpenAI(base_url="https://api.meta.ai/v1", api_key=env["META_API_KEY"]) as api:
        t = time.time()
        r = await api.chat.completions.create(model="muse-spark-1.3", reasoning_effort="medium", max_completion_tokens=8000,
                                              response_format={"type": "json_schema", "json_schema": {"name": "Glomeruli", "strict": True, "schema": SCHEMA}},
                                              messages=[{"role": "user", "content": [{"type": "text", "text": PROMPT}, {"type": "image_url", "image_url": {"url": url}}]}])
        out = json.loads(r.choices[0].message.content)
        print(f"Spark 1.3: {len(out['glomeruli'])} boxes in {time.time()-t:.1f}s; notes: {out['notes'][:200]}", flush=True)
        boxes = []
        for g in out["glomeruli"]:
            l, tp, rt, bt = (int(round(v * W / 1000)) for v in (g["x1"], g["y1"], g["x2"], g["y2"]))
            l, rt = sorted((max(0, min(W - 1, l)), max(1, min(W, rt)))); tp, bt = sorted((max(0, min(H - 1, tp)), max(1, min(H, bt))))
            if rt - l >= 10 and bt - tp >= 10:
                boxes.append((l, tp, rt, bt, g["confidence"]))
        box_mask = np.zeros((H, W), bool)
        for l, tp, rt, bt, _ in boxes:
            box_mask[tp:bt, l:rt] = True
        print("  Spark boxes alone:", nphs1_eval(box_mask) if boxes else "none", flush=True)
        if not boxes:
            return
        prompt = build_object_prompt(size=(W, H), objects=[PromptObject(id=i + 1, prompts=[FramePrompt(box=PromptBox(left=l, top=tp, right=rt, bottom=bt))])
                                                            for i, (l, tp, rt, bt, _) in enumerate(boxes[:16])])
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

        t = time.time()
        stream = await api.responses.create(model="sam-3.1", stream=True, input=[{"type": "message", "role": "user", "content": [
            {"type": "input_text", "text": prompt}, {"type": "input_image", "image_url": url}]}])
        async with stream, aclosing(events(stream)) as evs:
            res = await parse_responses_stream(evs, image_segmentation_format()).final_result()
    rec_boxes = {r.object_id: r for r in res.records if r.kind == "box"}
    mask = np.zeros((H, W), bool); objs = []
    for rec in (r for r in res.records if r.kind == "mask"):
        b, m = rec_boxes[rec.object_id], rec.mask
        local = np.frombuffer(decode_mask_to_raster(m), dtype=np.uint8).reshape(m.height, m.width).astype(bool)
        mask[b.top:b.top + m.height, b.left:b.left + m.width] |= local
        objs.append({"id": rec.object_id, "area_um2": int(local.sum())})
    ev = nphs1_eval(mask)
    print(f"SAM 3.1 box-prompted: {len(objs)} masks in {time.time()-t:.1f}s; {ev}; areas={[o['area_um2'] for o in objs]}", flush=True)
    img = Image.open(io.BytesIO(png)).convert("RGB"); d = ImageDraw.Draw(img)
    for l, tp, rt, bt, _ in boxes:
        d.rectangle([l, tp, rt, bt], outline=(255, 120, 0), width=2)
    arr = np.asarray(img).copy()
    edge = mask ^ np.asarray(Image.fromarray(mask.astype(np.uint8) * 255).filter(ImageFilter.MinFilter(5))).astype(bool)
    arr[edge] = [0, 200, 255]; arr[py, px] = [230, 180, 0]
    Image.fromarray(arr).save(OUT / "overlay_spark_boxes_sam_masks.png")
    (OUT / "sam_spike2.json").write_text(json.dumps({"spark_boxes": boxes, "spark_notes": out["notes"], "spark_box_eval": nphs1_eval(box_mask),
                                                     "sam_eval": ev, "sam_objects": objs}, indent=1))


asyncio.run(main())
