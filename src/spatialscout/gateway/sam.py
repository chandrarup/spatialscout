"""SAM 3.1 box-prompt segmentation: build the prompt, parse the streamed response with `meta-sam-parser`.

Masks come back as box-local crops (live-verified Nov 2): the mask raster's size equals its box, and a mask pixel
(x, y) sits at frame pixel (box.left + x, box.top + y). Boxes are half-open: `right` and `bottom` are exclusive.
Concept prompts find nothing on RNA-rendered images, so only box prompts are offered (ADR-0005).
"""

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
from meta_sam_parser import (
    FramePrompt,
    PromptBox,
    PromptObject,
    build_object_prompt,
    decode_mask_to_raster,
    image_segmentation_format,
    parse_responses_stream,
)

MAX_PROMPTED_OBJECTS = 16


@dataclass(frozen=True)
class Box:
    """A box in image pixels, half-open: it covers columns left..right-1 and rows top..bottom-1."""

    left: int
    top: int
    right: int
    bottom: int


@dataclass(frozen=True)
class SegmentedObject:
    """One prompted object: SAM's box and its box-local mask (True inside the object)."""

    object_id: int
    box: Box
    mask: np.ndarray

    def place(self, width: int, height: int) -> np.ndarray:
        """This object's mask in frame pixels: a (height, width) boolean image."""
        frame = np.zeros((height, width), dtype=bool)
        h, w = self.mask.shape
        frame[self.box.top : self.box.top + h, self.box.left : self.box.left + w] = self.mask
        return frame


@dataclass(frozen=True)
class Segmentation:
    width: int
    height: int
    objects: list[SegmentedObject]


def box_prompt(width: int, height: int, boxes: Sequence[Box]) -> str:
    """The prompt text for up to 16 boxes, numbered from 1 in the order given."""
    if not 1 <= len(boxes) <= MAX_PROMPTED_OBJECTS:
        raise ValueError(f"SAM 3.1 takes 1 to {MAX_PROMPTED_OBJECTS} prompted boxes, not {len(boxes)}")
    objects = [
        PromptObject(id=i + 1, prompts=[FramePrompt(box=PromptBox(left=b.left, top=b.top, right=b.right, bottom=b.bottom))])
        for i, b in enumerate(boxes)
    ]
    return build_object_prompt(size=(width, height), objects=objects)


async def parse_segmentation(events: Sequence[dict[str, Any]], width: int, height: int) -> Segmentation:
    """Parse recorded or live response events into objects with box-local masks."""
    result = await parse_responses_stream(_with_text_done(events), image_segmentation_format()).final_result()
    boxes = {r.object_id: r for r in result.records if r.kind == "box"}
    objects = []
    for record in (r for r in result.records if r.kind == "mask"):
        box = boxes[record.object_id]
        mask = record.mask
        raster = np.frombuffer(decode_mask_to_raster(mask), dtype=np.uint8).reshape(mask.height, mask.width).astype(bool)
        objects.append(
            SegmentedObject(
                object_id=int(record.object_id),
                box=Box(int(box.left), int(box.top), int(box.right), int(box.bottom)),
                mask=raster,
            )
        )
    return Segmentation(width=width, height=height, objects=sorted(objects, key=lambda o: o.object_id))


async def _with_text_done(events: Sequence[dict[str, Any]]) -> AsyncIterator[dict[str, Any]]:
    """Meta's cookbook workaround (as in `spikes/sam_spike3.py`): the parser closes a lane on
    `response.output_text.done`, which the API has not always sent, so synthesise it from
    `response.content_part.done`, once per lane."""
    done: set[tuple[Any, Any, Any]] = set()
    for event in events:
        lane = (event.get("item_id"), event.get("output_index"), event.get("content_index"))
        if event.get("type") == "response.output_text.done":
            if lane not in done:
                done.add(lane)
                yield event
            continue
        part = event.get("part")
        if event.get("type") == "response.content_part.done" and lane not in done and isinstance(part, dict) and part.get("type") == "output_text":
            done.add(lane)
            yield {
                "type": "response.output_text.done",
                "item_id": event.get("item_id"),
                "output_index": event.get("output_index"),
                "content_index": event.get("content_index"),
                "text": part.get("text", ""),
            }
        yield event
