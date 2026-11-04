"""The structure finder (exploratory, ADR-0005 narrowed by ADR-0006): SAM 3.1 glomerulus outlines from box prompts
on a gene-agnostic nucleus image.

1. Render each crop from nucleus positions and sizes only: no gene and no cell type label reaches the image.
2. Seed one box per glomerulus from merged NPHS1 clusters (`structures.seed_glomeruli`), or take a box the researcher
   drew.
3. Send up to 16 boxes per crop to SAM 3.1 through the model gateway, which replays stored responses or calls live.
4. Place each box-local mask in section µm, judge it on geometry alone, and compare it with its seed box and the
   convex hull of its NPHS1 clusters.

Every image sent is counted, with its cost, in the run.
"""

import hashlib
import math
import struct
import zlib
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from scipy import ndimage

from ..contracts import (
    CacheInput,
    ModelCallRecord,
    Region,
    ReplayInfo,
    StructureMask,
    StructureProposal,
    StructureRun,
    StructureSeed,
    content_id,
)
from ..data import SectionTables
from ..gateway import Box, ModelGateway, Segmentation
from ..gateway.providers import LIST_PRICES
from .structures import (
    COMPARISON_RULE,
    MAX_SEED_SIDE_UM,
    REJECTION_RULE,
    SEEDING_RULE,
    Crop,
    compare_shapes,
    judge_proposal,
    place_outline,
    seed_glomeruli,
)

MASK_VERSION = "sam31-boxprompt-v1"
SAM_MODEL = "sam-3.1"
CROP_SIZE_PX = 1024
MAX_BOXES_PER_IMAGE = 16
CROP_MARGIN_UM = 32.0
USER_BOX_MARGIN_UM = 128.0
BACKGROUND = (244, 226, 236)  # eosin pink
NUCLEUS = (72, 52, 140)  # hematoxylin purple
MIN_NUCLEUS_RADIUS_PX = 1.5
BLUR_SIGMA_PX = 0.8
RENDERING_RULE = (
    "Gene-agnostic: each cell with a detected nucleus is a hematoxylin-purple disc of the nucleus's area (radius at "
    f"least {MIN_NUCLEUS_RADIUS_PX:g} px) at its centroid, on an eosin-pink background, at 1 px = 1 µm, softened by a "
    f"Gaussian blur of {BLUR_SIGMA_PX:g} px. No gene and no cell type label is drawn. Crops are at most "
    f"{CROP_SIZE_PX} px square and hold whole seed boxes, at most {MAX_BOXES_PER_IMAGE} per image."
)
# Only what shapes the request (the image and its boxes) keys the stored responses; judging and comparing are
# recomputed from them, so changing those rules never needs a new live call.
RENDERING_SHA256 = hashlib.sha256("\n".join([RENDERING_RULE, SEEDING_RULE]).encode()).hexdigest()


# The demo sections: Control x1 and x2, DKD x3, x4 and x5 (GSE286184).
DEMO_SECTIONS = ("GSM8720409", "GSM8720410", "GSM8720411", "GSM8720412", "GSM8720413")
SAM_RECORDINGS_DIR = "sam"  # under the fixtures directory; kept out of `make fixtures`, since only a live call can record SAM


def recording_path(fixtures_dir: Path, name: str) -> Path:
    """Stored SAM 3.1 responses: `fixtures/sam/<section_id>.json` for a section's run, `user_boxes.json` for drawn boxes."""
    return Path(fixtures_dir) / SAM_RECORDINGS_DIR / f"{name}.json"


def run_path(artifacts_dir: Path, section_id: str) -> Path:
    """A GSE286184 section's committed structure-finder run."""
    return Path(artifacts_dir) / "GSE286184" / "structures" / f"{section_id}.json"


def recording_info(name: str) -> ReplayInfo:
    return ReplayInfo(
        recording_id=f"sam-{name}",
        recorded_at=datetime.now(UTC).replace(microsecond=0),
        origin="live",
        question=f"SAM 3.1 structure finder: {name}",
        note="Recorded by `spatialscout structures --run-mode live` (or the box-prompt route, live); exploratory outlines (ADR-0006).",
    )


# --- rendering ----------------------------------------------------------------------------------------------------


def render_nucleus_png(section: SectionTables, crop: Crop) -> bytes:
    """The crop as an RGB PNG of nucleus discs, written with zlib so no imaging library is needed."""
    width, height = crop.width, crop.height
    ink = np.zeros((height, width), dtype=float)
    cells = section.cells
    x = cells["x"].to_numpy(dtype=float)
    y = cells["y"].to_numpy(dtype=float)
    area = cells["nucleus_area"].to_numpy(dtype=float)
    radius = np.sqrt(np.where(np.isfinite(area), np.maximum(area, 1.0), np.nan) / math.pi)
    radius = np.maximum(radius, MIN_NUCLEUS_RADIUS_PX)
    cx, cy = (x - crop.x0) / crop.um_per_px, (y - crop.y0) / crop.um_per_px
    visible = np.isfinite(radius) & (cx + radius >= 0) & (cx - radius < width) & (cy + radius >= 0) & (cy - radius < height)
    for px, py, r in zip(cx[visible], cy[visible], radius[visible] / crop.um_per_px, strict=True):
        i0, i1 = max(0, int(math.floor(px - r))), min(width, int(math.ceil(px + r)) + 1)
        j0, j1 = max(0, int(math.floor(py - r))), min(height, int(math.ceil(py + r)) + 1)
        ii, jj = np.meshgrid(np.arange(i0, i1) + 0.5, np.arange(j0, j1) + 0.5)
        ink[j0:j1, i0:i1] = np.maximum(ink[j0:j1, i0:i1], (ii - px) ** 2 + (jj - py) ** 2 <= r * r)
    ink = ndimage.gaussian_filter(ink, BLUR_SIGMA_PX, mode="constant")
    rgb = np.stack([np.array(BACKGROUND[c]) + (NUCLEUS[c] - BACKGROUND[c]) * ink for c in range(3)], axis=-1)
    return _png(np.clip(np.rint(rgb), 0, 255).astype(np.uint8))


def _png(rgb: np.ndarray) -> bytes:
    height, width, _ = rgb.shape
    rows = b"".join(b"\x00" + rgb[j].tobytes() for j in range(height))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b"")


# --- crops --------------------------------------------------------------------------------------------------------


def plan_crops(seeds: Sequence[StructureSeed], size: int = CROP_SIZE_PX) -> list[tuple[Crop, list[StructureSeed]]]:
    """Group seed boxes into crops: in reading order, each unplaced seed opens a crop whose top-left corner is its
    box's, less a margin, and takes every unplaced seed lying wholly inside it with that margin to spare, up to 16, so
    a mask reaching a little past its box is not clipped by the image edge."""
    margin = CROP_MARGIN_UM
    remaining = sorted(seeds, key=lambda s: (s.box.y0, s.box.x0))
    crops: list[tuple[Crop, list[StructureSeed]]] = []
    while remaining:
        first = remaining[0]
        crop = Crop(x0=float(math.floor(first.box.x0 - margin)), y0=float(math.floor(first.box.y0 - margin)), width=size, height=size)
        members = [s for s in remaining if _within(s.box, crop, margin)][:MAX_BOXES_PER_IMAGE]
        if first not in members:  # a box too large for any crop is never sent; the caller rejects it first
            members = [first]
        crops.append((crop, members))
        remaining = [s for s in remaining if s not in members]
    return crops


def _within(b: Region, crop: Crop, margin: float) -> bool:
    x1, y1 = crop.x0 + crop.width * crop.um_per_px, crop.y0 + crop.height * crop.um_per_px
    return crop.x0 + margin <= b.x0 + 1 and b.x1 <= x1 - margin and crop.y0 + margin <= b.y0 + 1 and b.y1 <= y1 - margin


def box_in_pixels(b: Region, crop: Crop) -> Box:
    """A µm box as a half-open pixel box of the crop, grown outward to whole pixels."""
    s = crop.um_per_px
    return Box(
        left=max(0, int(math.floor((b.x0 - crop.x0) / s))),
        top=max(0, int(math.floor((b.y0 - crop.y0) / s))),
        right=min(crop.width, int(math.ceil((b.x1 - crop.x0) / s))),
        bottom=min(crop.height, int(math.ceil((b.y1 - crop.y0) / s))),
    )


# --- runs ---------------------------------------------------------------------------------------------------------


async def find_structures(
    section: SectionTables,
    gateway: ModelGateway,
    run_mode: str,
    *,
    log: Callable[[str], None] = lambda line: None,
) -> StructureRun:
    """SAM 3.1 outlines for every NPHS1 seed of a section. Seeds too large for one glomerulus are rejected unsent."""
    seeds = seed_glomeruli(section)
    sendable = [s for s in seeds if max(s.box.x1 - s.box.x0, s.box.y1 - s.box.y0) <= MAX_SEED_SIDE_UM]
    return await _run(section, gateway, run_mode, seeds, plan_crops(sendable), log)


async def outline_box(section: SectionTables, box: Region, gateway: ModelGateway, run_mode: str) -> StructureRun:
    """A SAM 3.1 outline for one box the researcher drew, in section µm, on a crop around it."""
    if box.section_id != section.section_id:
        raise ValueError(f"the box is on section {box.section_id}, not {section.section_id}")
    if not (box.x1 > box.x0 and box.y1 > box.y0):
        raise ValueError("the box needs a positive width and height")
    side = max(box.x1 - box.x0, box.y1 - box.y0) + 2 * USER_BOX_MARGIN_UM
    if side > CROP_SIZE_PX:
        raise ValueError(f"the box is too large: at most {CROP_SIZE_PX - 2 * USER_BOX_MARGIN_UM:g} µm on a side")
    seed = StructureSeed(
        seed_id=content_id("box", [section.section_id, box.x0, box.y0, box.x1, box.y1]),
        section_id=section.section_id,
        origin="user_box",
        box=box,
    )
    size = int(math.ceil(side))
    crop = Crop(x0=float(math.floor(box.x0 - USER_BOX_MARGIN_UM)), y0=float(math.floor(box.y0 - USER_BOX_MARGIN_UM)), width=size, height=size)
    return await _run(section, gateway, run_mode, [seed], [(crop, [seed])], lambda line: None)


async def _run(
    section: SectionTables,
    gateway: ModelGateway,
    run_mode: str,
    seeds: Sequence[StructureSeed],
    crops: list[tuple[Crop, list[StructureSeed]]],
    log: Callable[[str], None],
) -> StructureRun:
    inputs = [CacheInput(name="structure_finder", version="nucleus-render-v1", sha256=RENDERING_SHA256)]
    results: dict[str, tuple[int, Crop, object]] = {}
    records: list[ModelCallRecord] = []
    for index, (crop, members) in enumerate(crops):
        png = render_nucleus_png(section, crop)
        boxes = [box_in_pixels(s.box, crop) for s in members]
        segmentation, record = await gateway.segment_boxes(f"structures:{section.section_id}:{index}", png, crop.width, crop.height, boxes, inputs)
        records.append(record)
        log(f"{section.section_id}: image {index + 1}/{len(crops)} ({crop.width}x{crop.height} px, {len(members)} boxes) "
            f"{record.source} {record.latency_ms} ms")
        for position, seed in enumerate(members, start=1):
            results[seed.seed_id] = (index, crop, _object(segmentation, position))

    run_id = content_id("srun", [section.section_id, MASK_VERSION, [r.cache_key for r in records]])
    proposals, structures = [], []
    for seed in seeds:
        if seed.seed_id not in results:
            proposals.append(StructureProposal(
                seed=seed, status="rejected", reason=f"the seed box is larger than {MAX_SEED_SIDE_UM:g} µm on a side, so it was not sent",
                comparisons=compare_shapes(section, seed, None),
            ))
            continue
        index, crop, obj = results[seed.seed_id]
        placed = place_outline(obj, crop) if obj is not None else None
        status, reason = judge_proposal(seed, placed, crop)
        keep = status in ("outlined", "fragmented")
        structure_id = f"{seed.seed_id.replace('-seed-', '-glomerulus-')}" if seed.origin == "nphs1_clusters" else f"{seed.seed_id}-outline"
        if keep:
            structures.append(StructureMask(
                structure_id=structure_id, section_id=section.section_id, kind="glomerulus", outline=placed.outline,
                source="sam-3.1", mask_version=MASK_VERSION, run_id=run_id, seed_id=seed.seed_id,
            ))
        proposals.append(StructureProposal(
            seed=seed, status=status, reason=reason, structure_id=structure_id if keep else None,
            fragments=placed.fragments if placed else 0, crop_index=index,
            comparisons=compare_shapes(section, seed, placed.outline if placed and placed.outline else None),
        ))
    live_cost = sum(r.estimated_cost_usd or 0.0 for r in records)
    list_cost = len(records) * LIST_PRICES.per_image[SAM_MODEL]
    cost = round(live_cost if run_mode == "live" else list_cost, 6)
    log(f"{section.section_id}: {len(records)} images sent to SAM 3.1, ${cost:.4f} "
        f"({'live spend' if run_mode == 'live' else 'list price; served from stored responses'})")
    return StructureRun(
        run_id=run_id,
        mask_version=MASK_VERSION,
        dataset_id=section.dataset_id,
        section_id=section.section_id,
        model=SAM_MODEL,
        run_mode="live" if run_mode == "live" else "cached_tool_rerun",
        seeding_rule=SEEDING_RULE,
        rendering_rule=RENDERING_RULE,
        rejection_rule=REJECTION_RULE,
        images_sent=len(records),
        estimated_cost_usd=cost,
        crops=[Region(section_id=section.section_id, x0=c.x0, y0=c.y0, x1=c.x0 + c.width * c.um_per_px, y1=c.y0 + c.height * c.um_per_px) for c, _ in crops],
        proposals=proposals,
        structures=structures,
    )


def _object(segmentation: Segmentation, object_id: int):
    return next((o for o in segmentation.objects if o.object_id == object_id), None)
