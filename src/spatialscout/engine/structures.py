"""The structure finder's deterministic steps (ADR-0005, narrowed by ADR-0006): render a gene-agnostic nucleus image,
seed one box per glomerulus from merged NPHS1 clusters, and turn SAM 3.1's box-local masks into outlines in
section coordinates. The model call itself goes through the gateway (`spatialscout.structures`).

Coordinates: a crop is a window of the section rendered at `um_per_px`. Pixel (i, j) covers
[x0 + i·s, x0 + (i + 1)·s) × [y0 + j·s, y0 + (j + 1)·s) µm, with s = `um_per_px`.
"""

from dataclasses import dataclass

import contourpy
import numpy as np
from scipy import ndimage, sparse
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

from ..contracts import Region, StructureSeed
from ..data import SectionTables
from ..gateway import SegmentedObject


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
    return PlacedOutline(outline=_trace(largest, crop), fragments=int(fragments), pixel_area_um2=pixel_area)


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
