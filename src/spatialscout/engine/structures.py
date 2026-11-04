"""The structure finder's deterministic steps (ADR-0005, narrowed by ADR-0006): render a gene-agnostic nucleus image,
seed one box per glomerulus from merged NPHS1 clusters, and turn SAM 3.1's box-local masks into outlines in
section coordinates. The model call itself goes through the gateway (`spatialscout.structures`).

Coordinates: a crop is a window of the section rendered at `um_per_px`. Pixel (i, j) covers
[x0 + i·s, x0 + (i + 1)·s) × [y0 + j·s, y0 + (j + 1)·s) µm, with s = `um_per_px`.
"""

import math
from dataclasses import dataclass
from typing import Literal

import contourpy
import numpy as np
from matplotlib.path import Path as MplPath
from scipy import ndimage, sparse
from scipy.sparse.csgraph import connected_components
from scipy.spatial import ConvexHull, QhullError, cKDTree

from ..contracts import ConditionName, OutlineMeasures, Region, StructureMask, StructureSeed
from ..data import SectionTables
from ..gateway import SegmentedObject
from .conditions import inclusion_mask, structure_index


# --- seeding ------------------------------------------------------------------------------------------------------

SEED_GENE = "NPHS1"
CLUSTER_RADIUS_UM = 25.0
CLUSTER_MIN_NEIGHBOURS = 8
MERGE_GAP_UM = 40.0
SEED_PADDING_UM = 15.0
SEEDING_RULE = (
    f"{SEED_GENE} molecules are clustered by density (DBSCAN: radius {CLUSTER_RADIUS_UM:g} µm, at least "
    f"{CLUSTER_MIN_NEIGHBOURS} {SEED_GENE} molecules within it, the molecule included). Clusters whose bounding boxes "
    f"lie within {MERGE_GAP_UM:g} µm of each other are merged, repeatedly, into one seed per glomerulus; each seed box is "
    f"the merged clusters' bounding box padded by {SEED_PADDING_UM:g} µm. {SEED_GENE} seeds the boxes, so it never "
    "judges an outline."
)


def seed_glomeruli(section: SectionTables) -> list[StructureSeed]:
    """One seed box per glomerulus: density clusters of NPHS1 molecules, merged when their boxes nearly touch."""
    molecules = section.molecules
    points = molecules.loc[molecules["gene"] == SEED_GENE, ["x", "y"]].to_numpy(dtype=float)
    boxes = [_bounds(points[members]) + [1, len(members)] for members in _dbscan(points)]
    boxes = _merge(boxes)
    boxes.sort(key=lambda b: (b[1], b[0]))
    pad = SEED_PADDING_UM
    return [
        StructureSeed(
            seed_id=f"{section.section_id}-seed-{i:03d}",
            section_id=section.section_id,
            origin="nphs1_clusters",
            box=Region(section_id=section.section_id, x0=round(x0 - pad, 3), y0=round(y0 - pad, 3), x1=round(x1 + pad, 3), y1=round(y1 + pad, 3)),
            nphs1_molecules=int(n),
            clusters_merged=int(k),
        )
        for i, (x0, y0, x1, y1, k, n) in enumerate(boxes, start=1)
    ]


def seed_points(section: SectionTables, seed: StructureSeed) -> np.ndarray:
    """The NPHS1 molecules of a seed's clusters: those inside its box that belong to a density cluster."""
    molecules = section.molecules
    points = molecules.loc[molecules["gene"] == SEED_GENE, ["x", "y"]].to_numpy(dtype=float)
    clustered = np.concatenate([points[m] for m in _dbscan(points)]) if len(points) else np.empty((0, 2))
    b = seed.box
    inside = (clustered[:, 0] >= b.x0) & (clustered[:, 0] <= b.x1) & (clustered[:, 1] >= b.y0) & (clustered[:, 1] <= b.y1)
    return clustered[inside]


def _dbscan(points: np.ndarray) -> list[np.ndarray]:
    """DBSCAN clusters as index arrays: core points (enough neighbours) linked within the radius, plus the border
    points within the radius of a core point (each given to its nearest core point's cluster)."""
    if len(points) == 0:
        return []
    tree = cKDTree(points)
    neighbours = tree.query_ball_point(points, CLUSTER_RADIUS_UM)
    core = np.flatnonzero(np.array([len(n) for n in neighbours]) >= CLUSTER_MIN_NEIGHBOURS)
    if len(core) == 0:
        return []
    pairs = cKDTree(points[core]).query_pairs(CLUSTER_RADIUS_UM, output_type="ndarray")
    graph = sparse.coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(len(core), len(core)))
    _, labels = connected_components(graph, directed=False)
    cluster = np.full(len(points), -1)
    cluster[core] = labels
    border = np.flatnonzero(cluster < 0)
    if len(border):
        distance, nearest = cKDTree(points[core]).query(points[border])
        near = distance <= CLUSTER_RADIUS_UM
        cluster[border[near]] = labels[nearest[near]]
    return [np.flatnonzero(cluster == k) for k in range(labels.max() + 1)]


def _bounds(points: np.ndarray) -> list[float]:
    return [float(points[:, 0].min()), float(points[:, 1].min()), float(points[:, 0].max()), float(points[:, 1].max())]


def _merge(boxes: list[list[float]]) -> list[list[float]]:
    """Merge boxes [x0, y0, x1, y1, clusters, molecules] lying within the merge gap, until none do."""
    boxes = [list(b) for b in boxes]
    merged = True
    while merged:
        merged = False
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b = boxes[i], boxes[j]
                g = MERGE_GAP_UM
                if a[0] - g <= b[2] and b[0] - g <= a[2] and a[1] - g <= b[3] and b[1] - g <= a[3]:
                    boxes[i] = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]), a[4] + b[4], a[5] + b[5]]
                    del boxes[j]
                    merged = True
                    break
            if merged:
                break
    return boxes


# --- placement ----------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Crop:
    """A window of a section rendered as an image: its top-left corner in µm, its size in pixels and its scale."""

    x0: float
    y0: float
    width: int
    height: int
    um_per_px: float = 1.0

    def to_um(self, px: np.ndarray, py: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Continuous pixel coordinates (0 at the image's left or top edge) to section µm."""
        return self.x0 + px * self.um_per_px, self.y0 + py * self.um_per_px


SPECK_SHARE = 0.05


@dataclass(frozen=True)
class PlacedOutline:
    """One SAM object's mask in section coordinates: the outline of its largest connected piece (empty when the
    mask is empty), how many pieces the mask has, and the area of all its pixels in µm²."""

    outline: list[list[float]]
    fragments: int
    pixel_area_um2: float


def place_outline(obj: SegmentedObject, crop: Crop) -> PlacedOutline:
    """Place a box-local mask in its crop (`SegmentedObject.place`), then trace it in section µm."""
    frame = obj.place(crop.width, crop.height)
    pieces, fragments = ndimage.label(frame)
    pixel_area = float(frame.sum()) * crop.um_per_px**2
    if fragments == 0:
        return PlacedOutline(outline=[], fragments=0, pixel_area_um2=0.0)
    sizes = np.bincount(pieces.ravel())[1:]
    largest = pieces == (int(np.argmax(sizes)) + 1)
    # A speck (under 5% of the mask's pixels) is not counted as a fragment; its pixels still count toward the area.
    counted = int((sizes >= SPECK_SHARE * sizes.sum()).sum())
    return PlacedOutline(outline=_trace(largest, crop), fragments=counted, pixel_area_um2=pixel_area)


def _trace(mask: np.ndarray, crop: Crop) -> list[list[float]]:
    """The outer boundary of one connected mask piece, as a closed polygon in µm (first vertex not repeated)."""
    padded = np.pad(mask.astype(np.float64), 1)
    lines = contourpy.contour_generator(z=padded).lines(0.5)
    ring = max(lines, key=lambda line: abs(_signed_area(line)))
    # contour coordinates are padded array indices; index k is the centre of pixel k - 1, at continuous k - 0.5
    px, py = crop.to_um(ring[:, 0] - 0.5, ring[:, 1] - 0.5)
    points = [[round(float(x), 3), round(float(y), 3)] for x, y in zip(px, py, strict=True)]
    return points[:-1] if len(points) > 1 and points[0] == points[-1] else points


def _signed_area(line: np.ndarray) -> float:
    x, y = line[:, 0], line[:, 1]
    return float((x * np.roll(y, -1) - np.roll(x, -1) * y).sum() / 2)


# --- judging a proposal -------------------------------------------------------------------------------------------

MIN_AREA_SHARE_OF_SEED = 0.1
MAX_AREA_SHARE_OF_SEED = 2.0
MAX_SEED_SIDE_UM = 300.0
REJECTION_RULE = (
    "Geometry only; no gene judges a proposal. A seed box wider or taller than "
    f"{MAX_SEED_SIDE_UM:g} µm is rejected unsent (merged beyond one glomerulus). A proposal is empty when SAM 3.1 "
    f"returns no mask or an empty one; rejected when its mask covers less than {MIN_AREA_SHARE_OF_SEED:g}x or more "
    f"than {MAX_AREA_SHARE_OF_SEED:g}x the seed box's area, or its outline touches the image edge (clipped); "
    f"fragmented when the mask has several pieces of at least {SPECK_SHARE:.0%} of its pixels (the largest is "
    "outlined; smaller specks are ignored); otherwise outlined."
)

Status = Literal["outlined", "fragmented", "empty", "rejected"]


def judge_proposal(seed: StructureSeed, placed: PlacedOutline | None, crop: Crop) -> tuple[Status, str | None]:
    """A proposal's status and the reason, by the frozen geometric rejection rule."""
    if placed is None:
        return "empty", "SAM 3.1 returned no mask for this box"
    if placed.fragments == 0 or not placed.outline:
        return "empty", "SAM 3.1 returned an empty mask for this box"
    seed_area = (seed.box.x1 - seed.box.x0) * (seed.box.y1 - seed.box.y0)
    share = placed.pixel_area_um2 / seed_area if seed_area > 0 else math.inf
    if share < MIN_AREA_SHARE_OF_SEED:
        return "rejected", f"the mask covers {share:.2f}x the seed box's area, below {MIN_AREA_SHARE_OF_SEED:g}x"
    if share > MAX_AREA_SHARE_OF_SEED:
        return "rejected", f"the mask covers {share:.2f}x the seed box's area, above {MAX_AREA_SHARE_OF_SEED:g}x"
    xs = np.array([p[0] for p in placed.outline])
    ys = np.array([p[1] for p in placed.outline])
    edge = crop.um_per_px
    x1, y1 = crop.x0 + crop.width * crop.um_per_px, crop.y0 + crop.height * crop.um_per_px
    if xs.min() <= crop.x0 + edge or ys.min() <= crop.y0 + edge or xs.max() >= x1 - edge or ys.max() >= y1 - edge:
        return "rejected", "the outline touches the image edge, so the mask may be clipped"
    if placed.fragments > 1:
        return "fragmented", f"the mask has {placed.fragments} separate pieces; the largest is outlined"
    return "outlined", None


# --- comparing an outline with its seed box and the convex-hull baseline ------------------------------------------

LOCAL_MARGIN_UM = 100.0
CONSISTENCY_GENES = ("PECAM1", "PDGFRB")
COMPARISON_RULE = (
    "Each SAM 3.1 outline is measured beside its seed box and the convex hull of its seed's NPHS1 clusters, on a 1 µm "
    f"grid over the seed's local window (the box widened by {LOCAL_MARGIN_UM:g} µm on each side): area; the share of "
    "the seed box it covers; the retention the structure-constrained condition would cause with that shape as the "
    "only structure, over default molecules whose position or cell centroid lies inside it; and PECAM1 and PDGFRB "
    "consistency, each gene's molecule density inside the shape over its density in the rest of the window. "
    "NPHS1 seeded the box and is never measured."
)


def compare_shapes(section: SectionTables, seed: StructureSeed, outline: list[list[float]] | None) -> list[OutlineMeasures]:
    """The seed box, the convex hull of its NPHS1 clusters (NPHS1 seeds only) and the SAM 3.1 outline (when there
    is one), measured the same way."""
    b = seed.box
    m = LOCAL_MARGIN_UM
    window = Region(section_id=section.section_id, x0=b.x0 - m, y0=b.y0 - m, x1=b.x1 + m, y1=b.y1 + m)
    local = _local(section, window)
    gx, gy = np.meshgrid(np.arange(window.x0, window.x1) + 0.5, np.arange(window.y0, window.y1) + 0.5)
    grid_points = np.column_stack([gx.ravel(), gy.ravel()])
    in_box = _inside(_box_polygon(b), grid_points)
    shapes: list[tuple[str, list[list[float]] | None, str | None]] = [("seed_box", _box_polygon(b), None)]
    if seed.origin == "nphs1_clusters":
        hull = _hull(seed_points(section, seed))
        shapes.append(("convex_hull", hull, None if hull else "fewer than 3 non-collinear NPHS1 seed molecules"))
    if outline:
        shapes.append(("sam_outline", outline, None))
    return [_measure(kind, shape, reason, local, grid_points, in_box) for kind, shape, reason in shapes]


def _measure(kind, shape, reason, local: SectionTables, grid_points: np.ndarray, in_box: np.ndarray) -> OutlineMeasures:
    if shape is None:
        return OutlineMeasures(
            shape=kind, area_um2=None, seed_box_coverage=None, default_molecules=0, kept_molecules=0, retention=None,
            pecam1_enrichment=None, pdgfrb_enrichment=None, pecam1_share_inside=None, pdgfrb_share_inside=None,
            missing_reasons={"shape": reason or "no shape"},
        )
    inside = _inside(shape, grid_points)
    area = float(inside.sum())
    reasons: dict[str, str] = {}
    mask = StructureMask(structure_id="candidate", section_id=local.section_id, kind="glomerulus", outline=shape, source="sam-3.1")
    candidate = SectionTables(local.section_id, local.dataset_id, local.label_rule_id, local.molecules, local.cells, (mask,))
    molecules, cells = local.molecules, local.cells
    molecule_in = structure_index(candidate, molecules["x"].to_numpy(dtype=float), molecules["y"].to_numpy(dtype=float)) >= 0
    cell_flags = structure_index(candidate, cells["x"].to_numpy(dtype=float), cells["y"].to_numpy(dtype=float)) >= 0
    cell_in = dict(zip(cells["cell_id"].astype(str), cell_flags, strict=True))
    centroid_in = molecules["cell_id"].astype("string").fillna("").map(lambda c: bool(cell_in.get(c, False))).to_numpy(dtype=bool)
    default = inclusion_mask(candidate, ConditionName.DEFAULT)
    kept = inclusion_mask(candidate, ConditionName.STRUCTURE_CONSTRAINED)
    scope = default & (molecule_in | centroid_in)
    n_scope, n_kept = int(scope.sum()), int((scope & kept).sum())
    if not n_scope:
        reasons["retention"] = "no default-condition molecules inside the shape or assigned to a cell centred in it"
    consistency: dict[str, tuple[float | None, float | None]] = {}
    window_area = float(len(grid_points))
    genes = molecules["gene"].astype(str).to_numpy()
    for gene in CONSISTENCY_GENES:
        of_gene = genes == gene
        total, inner = int(of_gene.sum()), int((of_gene & molecule_in).sum())
        field = f"{gene.lower()}_enrichment"
        if total == 0:
            consistency[gene] = (None, None)
            reasons[field] = f"no {gene} molecules in the seed's local window"
            continue
        outer_density = (total - inner) / (window_area - area) if window_area > area else 0.0
        if outer_density == 0:
            consistency[gene] = (None, inner / total)
            reasons[field] = f"no {gene} molecules in the window outside the shape"
            continue
        consistency[gene] = ((inner / area) / outer_density if area else 0.0, inner / total)
    return OutlineMeasures(
        shape=kind,
        area_um2=area,
        seed_box_coverage=round(float((inside & in_box).sum()) / float(in_box.sum()), 6) if in_box.any() else None,
        default_molecules=n_scope,
        kept_molecules=n_kept,
        retention=n_kept / n_scope if n_scope else None,
        pecam1_enrichment=_round(consistency["PECAM1"][0]),
        pdgfrb_enrichment=_round(consistency["PDGFRB"][0]),
        pecam1_share_inside=_round(consistency["PECAM1"][1]),
        pdgfrb_share_inside=_round(consistency["PDGFRB"][1]),
        missing_reasons=reasons,
    )


def _round(value: float | None) -> float | None:
    return None if value is None else round(float(value), 6)


def _local(section: SectionTables, window: Region) -> SectionTables:
    """The molecules in a window and every cell they or the window hold, for measuring shapes inside it."""
    m, c = section.molecules, section.cells
    in_window = m["x"].between(window.x0, window.x1) & m["y"].between(window.y0, window.y1)
    cells_in = c["x"].between(window.x0, window.x1) & c["y"].between(window.y0, window.y1)
    wanted = set(m.loc[in_window, "cell_id"].dropna().astype(str)) | set(c.loc[cells_in, "cell_id"].astype(str))
    cells = c[c["cell_id"].astype(str).isin(wanted)].reset_index(drop=True)
    return SectionTables(section.section_id, section.dataset_id, section.label_rule_id, m[in_window].reset_index(drop=True), cells)


def _inside(polygon: list[list[float]], points: np.ndarray) -> np.ndarray:
    return MplPath(np.asarray(polygon, dtype=float)).contains_points(points)


def _box_polygon(b: Region) -> list[list[float]]:
    return [[b.x0, b.y0], [b.x1, b.y0], [b.x1, b.y1], [b.x0, b.y1]]


def _hull(points: np.ndarray) -> list[list[float]] | None:
    if len(points) < 3:
        return None
    try:
        hull = ConvexHull(points)
    except QhullError:
        return None
    return [[round(float(x), 3), round(float(y), 3)] for x, y in points[hull.vertices]]
