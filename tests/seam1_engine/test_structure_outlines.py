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

from spatialscout.contracts import OutlineMeasures, Recording
from spatialscout.data import make_section
from spatialscout.engine.structures import SEED_PADDING_UM, Crop, compare_shapes, place_outline, seed_glomeruli
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
    mask[9, 19] = True  # a 1 px speck, under 5% of the mask: not a fragment
    placed = place_outline(SegmentedObject(object_id=1, box=Box(5, 5, 25, 15), mask=mask), Crop(x0=0.0, y0=0.0, width=40, height=40))

    assert placed.fragments == 2
    area, x, y = polygon_area_and_centroid(placed.outline)
    assert (x, y) == (pytest.approx(5 + 5.0, abs=0.5), pytest.approx(5 + 5.0, abs=0.5))
    assert placed.pixel_area_um2 == 74


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


def test_outline_seed_box_and_convex_hull_are_measured_the_same_way_without_nphs1():
    """Seed box [100, 200]²; its NPHS1 cluster fills [110, 190]², so the hull is that square; the SAM outline is
    [125, 175]². The local window is the box widened by 100 µm: [0, 300]². 25 PECAM1 molecules lie inside the outline
    and 25 in the window's corner, outside every shape. Cell A (centroid 150, 150) has 2 molecules at its centroid
    and 2 at x = 180, outside the outline only. Cell B (centroid 195, 150, outside the hull) has 2 molecules at
    x = 196 and 1 at x = 205, outside the box."""
    seed_cluster = molecule_rows(grid(110, 110, 190, 190, 5), "NPHS1")
    pecam1 = molecule_rows(grid(130, 130, 170, 170, 10) + grid(10, 10, 50, 50, 10), "PECAM1", start=1000)
    a = molecule_rows([(150, 150), (150, 150), (180, 150), (180, 150)], "LRP2", start=2000, cell_id="A")
    b = molecule_rows([(196, 150), (196, 150), (205, 150)], "LRP2", start=3000, cell_id="B")
    cells = [
        {"cell_id": "A", "cell_type": "Podocyte", "x": 150.0, "y": 150.0, "nucleus_area": 20.0, "cell_area": 60.0},
        {"cell_id": "B", "cell_type": "PT", "x": 195.0, "y": 150.0, "nucleus_area": 20.0, "cell_area": 60.0},
    ]
    section = make_section("S1", "test", "full-panel-v1", molecules=seed_cluster + pecam1 + a + b, cells=cells)
    (seed,) = seed_glomeruli(section)
    seed = seed.model_copy(update={"box": seed.box.model_copy(update={"x0": 100.0, "y0": 100.0, "x1": 200.0, "y1": 200.0})})
    outline = [[125.0, 125.0], [175.0, 125.0], [175.0, 175.0], [125.0, 175.0]]

    measures = {m.shape: m for m in compare_shapes(section, seed, outline)}

    box, hull, sam = measures["seed_box"], measures["convex_hull"], measures["sam_outline"]
    assert (box.area_um2, hull.area_um2, sam.area_um2) == (10000, 6400, 2500)
    assert (box.seed_box_coverage, hull.seed_box_coverage, sam.seed_box_coverage) == (1.0, 0.64, 0.25)
    assert [(m.kept_molecules, m.default_molecules) for m in (box, hull, sam)] == [(6, 7), (4, 4), (2, 4)]
    assert sam.retention == 0.5
    assert box.pecam1_enrichment == pytest.approx((25 / 10000) / (25 / 80000))
    assert hull.pecam1_enrichment == pytest.approx((25 / 6400) / (25 / 83600))
    assert sam.pecam1_enrichment == pytest.approx((25 / 2500) / (25 / 87500))
    assert sam.pecam1_share_inside == 0.5
    assert sam.pdgfrb_enrichment is None and "pdgfrb_enrichment" in sam.missing_reasons
    assert not any("nphs1" in field for field in OutlineMeasures.model_fields)


def test_proposals_are_judged_on_geometry_alone():
    from spatialscout.engine.structures import PlacedOutline, judge_proposal

    seed = seed_glomeruli(nphs1_section(grid(100, 100, 140, 140, 5)))[0]  # box [85, 155]², 4900 µm²
    crop = Crop(x0=0.0, y0=0.0, width=1024, height=1024)
    ring = [[90.0, 90.0], [150.0, 90.0], [150.0, 150.0], [90.0, 150.0]]

    assert judge_proposal(seed, None, crop)[0] == "empty"
    assert judge_proposal(seed, PlacedOutline([], 0, 0.0), crop)[0] == "empty"
    assert judge_proposal(seed, PlacedOutline(ring, 1, 3600.0), crop) == ("outlined", None)
    assert judge_proposal(seed, PlacedOutline(ring, 3, 3700.0), crop)[0] == "fragmented"
    tiny = [[100.0, 100.0], [110.0, 100.0], [110.0, 110.0], [100.0, 110.0]]
    assert judge_proposal(seed, PlacedOutline(tiny, 1, 100.0), crop)[0] == "rejected"
    at_edge = Crop(x0=90.0, y0=0.0, width=1024, height=1024)
    assert judge_proposal(seed, PlacedOutline(ring, 1, 3600.0), at_edge)[0] == "rejected"


def test_the_nucleus_image_is_gene_agnostic_and_draws_each_nucleus_at_its_place():
    from spatialscout.engine.structure_finder import render_nucleus_png

    cells = [
        {"cell_id": "A", "cell_type": "Podocyte", "x": 20.0, "y": 10.0, "nucleus_area": math.pi * 16, "cell_area": 60.0},
        {"cell_id": "B", "cell_type": "PT", "x": 50.0, "y": 30.0, "nucleus_area": float("nan"), "cell_area": 60.0},
    ]
    nphs1 = make_section("S1", "test", "r", molecules=molecule_rows([(20, 10)], "NPHS1", cell_id="A"), cells=cells)
    relabelled = make_section("S1", "test", "r", molecules=molecule_rows([(20, 10)], "LRP2", cell_id="A"),
                              cells=[{**c, "cell_type": "TAL"} for c in cells])
    crop = Crop(x0=0.0, y0=0.0, width=64, height=48)

    png = render_nucleus_png(nphs1, crop)

    assert png == render_nucleus_png(relabelled, crop)
    pixels = decode_png(png)
    assert pixels.shape == (48, 64, 3)
    assert pixels[10, 20].tolist() != pixels[40, 60].tolist()  # A's nucleus (radius 4) is drawn; background elsewhere
    assert pixels[30, 50].tolist() == pixels[40, 60].tolist()  # B has no detected nucleus, so nothing is drawn


def decode_png(png: bytes) -> np.ndarray:
    import struct
    import zlib

    width, height = struct.unpack(">II", png[16:24])
    pos, data = 8, b""
    while pos < len(png):
        (length,) = struct.unpack(">I", png[pos : pos + 4])
        if png[pos + 4 : pos + 8] == b"IDAT":
            data += png[pos + 8 : pos + 8 + length]
        pos += 12 + length
    rows = zlib.decompress(data)
    stride = 1 + 3 * width
    assert all(rows[i * stride] == 0 for i in range(height))  # filter type 0 on every row
    return np.frombuffer(b"".join(rows[i * stride + 1 : (i + 1) * stride] for i in range(height)), dtype=np.uint8).reshape(height, width, 3)


def test_crops_hold_every_seed_whole_with_at_most_16_boxes_each():
    from spatialscout.engine.structure_finder import plan_crops

    patches = [grid(x, y, x + 30, y + 30, 5) for x in range(100, 4000, 120) for y in (100, 400)]  # 66 seeds
    seeds = seed_glomeruli(nphs1_section([p for patch in patches for p in patch]))

    crops = plan_crops(seeds)

    placed = [s.seed_id for _, members in crops for s in members]
    assert sorted(placed) == sorted(s.seed_id for s in seeds) and len(placed) == len(seeds) == 66
    for crop, members in crops:
        assert 1 <= len(members) <= 16
        for s in members:
            b = s.box
            assert crop.x0 <= b.x0 and b.x1 <= crop.x0 + crop.width and crop.y0 <= b.y0 and b.y1 <= crop.y0 + crop.height


def test_seeding_reads_only_nphs1():
    others = molecule_rows(grid(100, 100, 140, 140, 5), "PECAM1", start=10_000)

    assert seed_glomeruli(nphs1_section([], extra=others)) == []
