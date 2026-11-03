"""Seam 1: structure outlines, from SAM 3.1's box-local masks to section coordinates.

Placement runs on a recorded SAM 3.1 response to a synthetic image: the smoke image, a 96 x 64 PNG with two
filled discs drawn at known pixel centres and radii (`gateway.smoke.DISCS`), recorded live by `spatialscout smoke`.
The test checks coordinates, not anatomy: the image is pretended to be a crop whose top-left corner sits at
(1000, 2000) µm, at 2 µm per pixel, so each outline must land on its disc's centre and area in µm.
"""

import asyncio
import math
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest

from spatialscout.contracts import Recording
from spatialscout.data import make_section
from spatialscout.engine.structures import SEED_PADDING_UM, Crop, place_outline, seed_glomeruli
from spatialscout.gateway import ModelGateway, ReplaySource
from spatialscout.gateway.smoke import BOXES, DISCS, IMAGE_SIZE

SMOKE = Path(__file__).resolve().parents[2] / "fixtures" / "smoke"


def polygon_area_and_centroid(points):
    xs, ys = np.array([p[0] for p in points]), np.array([p[1] for p in points])
    cross = xs * np.roll(ys, -1) - np.roll(xs, -1) * ys
    area = cross.sum() / 2
    return abs(area), ((xs + np.roll(xs, -1)) * cross).sum() / (6 * area), ((ys + np.roll(ys, -1)) * cross).sum() / (6 * area)


@pytest.fixture(scope="module")
def segmentation():
    recording = Recording.model_validate_json((SMOKE / "recording.json").read_text(encoding="utf-8"))
    gateway = ModelGateway(ReplaySource(recording), lambda: datetime.now(UTC))
    width, height = IMAGE_SIZE
    seg, _ = asyncio.run(gateway.segment_boxes("smoke:sam", (SMOKE / "circles.png").read_bytes(), width, height, BOXES))
    return seg


def test_a_recorded_box_local_mask_lands_on_its_disc_in_section_micrometres(segmentation):
    crop = Crop(x0=1000.0, y0=2000.0, width=IMAGE_SIZE[0], height=IMAGE_SIZE[1], um_per_px=2.0)

    placed = [place_outline(obj, crop) for obj in segmentation.objects]

    assert len(placed) == len(DISCS) == 2
    for outline, (cx, cy, r) in zip(placed, DISCS, strict=True):
        area, x, y = polygon_area_and_centroid(outline.outline)
        # Pixel (i, j) covers [i, i + 1) x [j, j + 1), so a disc drawn around pixel index c is centred at c + 0.5.
        assert x == pytest.approx(1000 + 2 * (cx + 0.5), abs=2 * 1.0)
        assert y == pytest.approx(2000 + 2 * (cy + 0.5), abs=2 * 1.0)
        assert area == pytest.approx(math.pi * r * r * 4, rel=0.2)
        assert outline.fragments == 1
        assert outline.pixel_area_um2 == pytest.approx(math.pi * r * r * 4, rel=0.2)


def test_an_empty_mask_places_no_outline():
    from spatialscout.gateway import Box, SegmentedObject

    empty = SegmentedObject(object_id=1, box=Box(4, 4, 10, 10), mask=np.zeros((6, 6), dtype=bool))

    placed = place_outline(empty, Crop(x0=0.0, y0=0.0, width=20, height=20))

    assert placed.outline == [] and placed.fragments == 0 and placed.pixel_area_um2 == 0


def test_a_mask_in_two_pieces_reports_both_and_outlines_the_larger():
    from spatialscout.gateway import Box, SegmentedObject

    mask = np.zeros((10, 20), dtype=bool)
    mask[1:9, 1:9] = True  # 64 px
    mask[2:5, 14:17] = True  # 9 px, apart from the first
    placed = place_outline(SegmentedObject(object_id=1, box=Box(5, 5, 25, 15), mask=mask), Crop(x0=0.0, y0=0.0, width=40, height=40))

    assert placed.fragments == 2
    area, x, y = polygon_area_and_centroid(placed.outline)
    assert (x, y) == (pytest.approx(5 + 5.0, abs=0.5), pytest.approx(5 + 5.0, abs=0.5))
    assert placed.pixel_area_um2 == 73


# --- seeding: one box per glomerulus from merged NPHS1 clusters ---------------------------------------------------


def molecule_rows(points, gene, start=0, cell_id=None):
    return [
        {"molecule_id": f"m{start + i}", "gene": gene, "x": float(x), "y": float(y), "cell_id": cell_id,
         "overlaps_nucleus": False, "nucleus_distance": float("nan"), "qv": 40.0}
        for i, (x, y) in enumerate(points)
    ]


def grid(x0, y0, x1, y1, step):
    return [(x, y) for x in np.arange(x0, x1 + 1e-9, step) for y in np.arange(y0, y1 + 1e-9, step)]


def nphs1_section(points, extra=()):
    rows = molecule_rows(points, "NPHS1") + list(extra)
    return make_section("S1", "test", "full-panel-v1", molecules=rows, cells=[])


def test_two_nphs1_clusters_of_one_glomerulus_merge_into_one_padded_box_and_a_distant_one_stays_apart():
    # Two dense patches 30 µm apart (one glomerulus split by a density gap), and a third patch 500 µm away.
    left = grid(100, 100, 140, 140, 5)
    right = grid(170, 100, 210, 140, 5)
    far = grid(700, 600, 740, 640, 5)
    noise = [(400, 400), (900, 100)]  # isolated molecules seed nothing

    seeds = seed_glomeruli(nphs1_section(left + right + far + noise))

    pad = SEED_PADDING_UM
    assert [(s.box.x0, s.box.y0, s.box.x1, s.box.y1) for s in seeds] == [
        (100 - pad, 100 - pad, 210 + pad, 140 + pad),
        (700 - pad, 600 - pad, 740 + pad, 640 + pad),
    ]
    assert [s.clusters_merged for s in seeds] == [2, 1]
    assert [s.nphs1_molecules for s in seeds] == [len(left) + len(right), len(far)]
    assert seeds[0].seed_id == "S1-seed-001"


def test_seeding_reads_only_nphs1():
    others = molecule_rows(grid(100, 100, 140, 140, 5), "PECAM1", start=10_000)

    assert seed_glomeruli(nphs1_section([], extra=others)) == []
