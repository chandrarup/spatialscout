"""Measured molecule depth, kept beside the frozen analysis inputs rather than inside them.

`build_depth_sidecar` joins a section's validated molecules to the deposited transcripts table by transcript id and
refuses a join that is not one-to-one or whose x/y disagree. `depth_points` returns a box's molecules with z, sampled
deterministically for drawing; `depth_profile` counts every molecule in a box by depth interval, gene and condition.
Neither changes an audit, a claim or a recording.
"""

from collections.abc import Sequence

import numpy as np
import pandas as pd

from ..contracts import ConditionName, DepthBin, DepthPoints, DepthProfile, DepthSource, Region
from ..data import SectionTables
from .conditions import inclusion_mask

XY_TOLERANCE_UM = 0.01
STRICTER = ConditionName.NUCLEUS_ONLY
PROFILE_CONDITIONS = (ConditionName.DEFAULT, ConditionName.NUCLEUS_ONLY, ConditionName.DISTANCE_CAP_1UM, ConditionName.DISTANCE_CAP_2UM)


class DepthJoinError(ValueError):
    """The raw transcripts do not match the validated molecules one to one."""


def build_depth_sidecar(molecules: pd.DataFrame, raw: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float | int | None]]:
    """`molecules`: molecule_id, x, y. `raw`: transcript_id, x_location, y_location, z_location. Returns
    (molecule_id, z) in the molecules' order, and the join's counts. Missing z stays NaN and is counted."""
    ids = raw["transcript_id"].astype(str)
    if not ids.is_unique:
        raise DepthJoinError(f"{int(ids.duplicated().sum())} duplicate transcript ids in the raw table")
    table = pd.DataFrame({"transcript_id": ids, "rx": raw["x_location"].to_numpy(), "ry": raw["y_location"].to_numpy(), "z": raw["z_location"].to_numpy()})
    joined = molecules[["molecule_id", "x", "y"]].assign(molecule_id=molecules["molecule_id"].astype(str)).merge(
        table, left_on="molecule_id", right_on="transcript_id", how="left", validate="one_to_one"
    )
    unmatched = int(joined["transcript_id"].isna().sum())
    if unmatched:
        raise DepthJoinError(f"{unmatched} validated molecules have no raw transcript with the same id")
    disagreement = float(np.nanmax(np.abs(np.concatenate([joined["x"] - joined["rx"], joined["y"] - joined["ry"]])))) if len(joined) else 0.0
    if disagreement > XY_TOLERANCE_UM:
        raise DepthJoinError(f"x/y disagree by up to {disagreement:.3f} µm between the raw and validated rows")
    z = joined["z"].astype("float32")
    with_depth = int(z.notna().sum())
    stats: dict[str, float | int | None] = {
        "molecules": len(joined),
        "with_depth": with_depth,
        "missing_depth": len(joined) - with_depth,
        "max_xy_disagreement_um": disagreement,
        "z_min": float(z.min()) if with_depth else None,
        "z_max": float(z.max()) if with_depth else None,
    }
    return pd.DataFrame({"molecule_id": joined["molecule_id"], "z": z}), stats


_ALIGNED: dict[tuple[str, int, int, int], np.ndarray] = {}


def _aligned_z(section: SectionTables, sidecar: pd.DataFrame) -> np.ndarray:
    """z per molecule of the section, by molecule id (cached per section and sidecar). A section whose ids differ from
    the sidecar's fails. The sidecar is written in the molecule table's order, so equal id columns skip the lookup."""
    key = (section.section_id, id(section.molecules), id(sidecar), len(sidecar))
    if key not in _ALIGNED:
        if len(_ALIGNED) >= 4:
            _ALIGNED.pop(next(iter(_ALIGNED)))
        _ALIGNED[key] = _align(section, sidecar)
    return _ALIGNED[key]


def _align(section: SectionTables, sidecar: pd.DataFrame) -> np.ndarray:
    ids = section.molecules["molecule_id"].astype(str).to_numpy()
    side = sidecar["molecule_id"].astype(str).to_numpy()
    if len(side) == len(ids) and np.array_equal(side, ids):
        return sidecar["z"].to_numpy(dtype=np.float64)
    lookup = pd.Series(sidecar["z"].to_numpy(), index=sidecar["molecule_id"].astype(str).to_numpy())
    if not lookup.index.is_unique:
        raise DepthJoinError("the depth sidecar repeats a molecule id")
    missing = ~pd.Index(ids).isin(lookup.index)
    if missing.any():
        raise DepthJoinError(f"{int(missing.sum())} section molecules are absent from the depth sidecar")
    if len(lookup) != len(ids):
        raise DepthJoinError(f"the depth sidecar has {len(lookup)} molecules; the section has {len(ids)}")
    return lookup.reindex(ids).to_numpy(dtype=np.float64)


def _in_box(section: SectionTables, region: Region) -> np.ndarray:
    if region.section_id != section.section_id:
        raise ValueError(f"the box is on section {region.section_id}, not {section.section_id}")
    x = section.molecules["x"].to_numpy()
    y = section.molecules["y"].to_numpy()
    return (x >= region.x0) & (x <= region.x1) & (y >= region.y0) & (y <= region.y1)


def _population(section: SectionTables, cell_type: str | None) -> np.ndarray:
    if cell_type is None:
        return np.ones(len(section.molecules), dtype=bool)
    types = section.cells.set_index("cell_id")["cell_type"]
    return (section.molecules["cell_id"].map(types) == cell_type).fillna(False).to_numpy(dtype=bool)


def depth_points(
    section: SectionTables, sidecar: pd.DataFrame, region: Region, genes: Sequence[str], z_range: tuple[float, float] | None, budget: int
) -> DepthPoints:
    z = _aligned_z(section, sidecar)
    gene = section.molecules["gene"].to_numpy()
    scope = _in_box(section, region) & np.isin(gene, list(genes))
    lo, hi = z_range if z_range is not None else (float(np.nanmin(z)), float(np.nanmax(z)))
    eligible = scope & ~np.isnan(z) & (z >= lo) & (z <= hi)
    index = np.flatnonzero(eligible)
    if len(index) > budget:
        index = index[np.linspace(0, len(index) - 1, budget).astype(int)]
        sampling = f"every {len(np.flatnonzero(eligible)) / budget:.1f}th eligible molecule in table order (deterministic)"
    else:
        sampling = "all eligible molecules"
    assigned = inclusion_mask(section, ConditionName.DEFAULT)
    kept = assigned & inclusion_mask(section, STRICTER)
    order = {g: i for i, g in enumerate(genes)}
    m = section.molecules
    return DepthPoints(
        section_id=section.section_id,
        region=region,
        genes=list(genes),
        z_range=[lo, hi],
        total_in_box=int(scope.sum()),
        eligible=int(eligible.sum()),
        displayed=len(index),
        sampling=sampling,
        x=m["x"].to_numpy()[index].round(3).tolist(),
        y=m["y"].to_numpy()[index].round(3).tolist(),
        z=z[index].round(3).tolist(),
        gene_index=[order[g] for g in gene[index]],
        assigned=assigned[index].tolist(),
        kept_stricter=kept[index].tolist(),
        stricter_condition=STRICTER.value,
    )


def depth_profile(
    section: SectionTables, sidecar: pd.DataFrame, source: DepthSource, region: Region, genes: Sequence[str], bin_um: float, cell_type: str | None = None
) -> DepthProfile:
    """Counts every molecule in scope (never the drawn sample). Bins are half-open [z0, z1), the last one closed."""
    z = _aligned_z(section, sidecar)
    gene = section.molecules["gene"].to_numpy()
    scope = _in_box(section, region) & _population(section, cell_type)
    present = ~np.isnan(z)
    if present.any():
        start = np.floor(np.nanmin(z) / bin_um) * bin_um
        stop = max(np.ceil(np.nanmax(z) / bin_um) * bin_um, start + bin_um)
    else:
        start, stop = 0.0, bin_um
    edges = np.arange(start, stop + bin_um / 2, bin_um)
    masks = {"all": np.ones(len(gene), dtype=bool)}
    for condition in PROFILE_CONDITIONS:
        masks[condition.value] = inclusion_mask(section, condition)
    slot = np.clip(np.searchsorted(edges, np.where(present, z, start), side="right") - 1, 0, len(edges) - 2)
    bins = [DepthBin(z0=float(edges[i]), z1=float(edges[i + 1]), counts={}) for i in range(len(edges) - 1)]
    totals: dict[str, dict[str, int]] = {}
    missing: dict[str, int] = {}
    for g in genes:
        of_gene = scope & (gene == g)
        missing[g] = int((of_gene & ~present).sum())
        totals[g] = {}
        for name, mask in masks.items():
            chosen = of_gene & present & mask
            counts = np.bincount(slot[chosen], minlength=len(bins))
            totals[g][name] = int(counts.sum())
            for i, b in enumerate(bins):
                b.counts.setdefault(g, {})[name] = int(counts[i])
    return DepthProfile(
        dataset_id=section.dataset_id,
        section_id=section.section_id,
        label_rule_id=section.label_rule_id,
        region=region,
        scope="whose own x, y lie in the box" + (f", assigned by default to {cell_type} cells" if cell_type else ""),
        genes=list(genes),
        cell_type=cell_type,
        conditions=list(masks),
        bin_um=bin_um,
        bins=bins,
        totals=totals,
        missing_depth=missing,
        source=source,
    )
