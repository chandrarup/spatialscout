"""The protein-level audit on KPMP CODEX images (ticket 02c): the analogue of ADR-0002 for antibody images.

A CODEX image has a fixed segmentation mask, so instead of assignment conditions over molecules, each cell's marker
signal is measured under four measurement conditions, each a subset of the cell's mask pixels:

- `whole_cell`: every pixel of the cell's label (the default)
- `eroded_1px`, `eroded_2px`: pixels whose 3 x 3 (5 x 5) neighbourhood lies entirely inside the cell, so signal on
  the boundary, where a neighbour's membrane stain spills over, is dropped
- `nucleus_region`: pixels of the cell whose DAPI is at or above a frozen threshold

Lateral spillover from a neighbouring cell is the protein counterpart of molecule admixture. Everything here is
deterministic NumPy on the mask and images; channels are read one at a time, and per-cell sums use `np.bincount`.
"""

import csv
import io
from collections.abc import Callable, Mapping

import numpy as np
import pandas as pd
from scipy import ndimage
from scipy.special import ndtr

from ..contracts import EvidenceStatus, ProteinAuditResult, ProteinConditionRow, ProteinThreshold, Region, content_id

MEASUREMENT_CONDITIONS = ("whole_cell", "eroded_1px", "eroded_2px", "nucleus_region")
PRIMARY_STRICTER = ("eroded_1px", "eroded_2px", "nucleus_region")
DATASET = "KPMP-CODEX"
POPULATION_GATE_MIN_CELLS = 20
POSITIVE_GATE_MIN_CELLS = 10
EXCESS_LOG2_DROP = 0.5
THRESHOLD_FACTOR = 2.0**-EXCESS_LOG2_DROP
BORDER_REACH_PX = 2

THRESHOLD_RULE = (
    "Otsu's threshold on the healthy reference's whole-cell means of the marker (256 bins of width 1 on 0-255): the "
    "first split maximising the between-class variance; a cell is positive when its mean is at or above it. The same "
    "value is applied to every participant and every measurement condition."
)
POPULATION_RULE = "Cells positive for the population marker as whole cells; frozen for every measurement condition."
HOME_RULE = "Cells positive for the marker as whole cells and not positive for the population marker."
BORDER_RULE = (
    f"Two cells border when a pixel of one lies within {BORDER_REACH_PX} px of a pixel of the other along a row or a "
    "column of the segmentation mask, so a one-pixel background gap between cells still counts."
)
EXPECTATION_RULE = (
    "Closed form. A condition keeping k of a cell's n pixels is compared with k pixels drawn at random: their mean "
    "has the whole-cell mean m and variance s^2 / k x (n - k) / (n - 1), with s^2 the whole-cell pixel variance, and "
    "reaches the threshold t with probability Phi((m - t) / sd) (1 or 0 when sd = 0; 0 when k = 0). Expected share: "
    "the mean of that probability over the population."
)
LABEL_RULE = (
    f"Gates: at least {POPULATION_GATE_MIN_CELLS} population cells and {POSITIVE_GATE_MIN_CELLS} of them positive for "
    "the marker as whole cells, else insufficient evidence. Segmentation-sensitive: under one stricter condition the "
    "observed share O is below the expectation E x 2^-0.5. Otherwise stable."
)
CAVEAT = (
    "Eroding a cell also removes genuine membrane signal, which random pixel loss does not model; compare the "
    "bordering-home shares of excluded and retained cells before reading an excess drop as spillover."
)
INFERENCE = "Descriptive only: one participant's section, with no leave-one-out; a participant compared with another is one person against one person."

Image = np.ndarray | Callable[[], np.ndarray]


def channel_index_by_marker(channel_key_csv: str) -> dict[str, int]:
    """Zero-based page index of each marker in a KPMP `*_ChannelKey.csv` (1-based `Channel`, `Marker`). Panels
    differ in order and content, so channels are always looked up by marker name."""
    rows = csv.DictReader(io.StringIO(channel_key_csv.lstrip("﻿")))
    return {row["Marker"].strip(): int(row["Channel"]) - 1 for row in rows}


def interior_pixels(labels: np.ndarray, erosion_px: int) -> np.ndarray:
    """Pixels whose (2e+1) x (2e+1) neighbourhood is entirely their own cell; outside the image is background."""
    size = 2 * erosion_px + 1
    low = ndimage.minimum_filter(labels, size=size, mode="constant", cval=0)
    high = ndimage.maximum_filter(labels, size=size, mode="constant", cval=0)
    return (labels > 0) & (low == labels) & (high == labels)


def _read(image: Image) -> np.ndarray:
    return image() if callable(image) else image


def measure_cells(
    labels: np.ndarray,
    channels: Mapping[str, Image],
    *,
    dapi: Image,
    nucleus_threshold: float,
    pixel_size_um: float,
) -> pd.DataFrame:
    """One row per cell label (> 0): area, centroid (pixel centres, µm, y down), and per measurement condition the
    pixels kept plus, per channel, the sum and sum of squares of the kept pixels. Means and variances derive from
    those (`cell_means`). A channel may be given as a callable so each is read only when measured."""
    flat = labels.ravel()
    ids = np.unique(flat[flat > 0])
    size = int(ids.max()) + 1 if len(ids) else 1
    selections: dict[str, np.ndarray] = {"whole_cell": flat > 0}
    selections["eroded_1px"] = interior_pixels(labels, 1).ravel()
    selections["eroded_2px"] = interior_pixels(labels, 2).ravel()
    selections["nucleus_region"] = (flat > 0) & (_read(dapi).ravel() >= nucleus_threshold)

    whole = selections["whole_cell"]
    rows, cols = np.divmod(np.flatnonzero(whole), labels.shape[1])
    counts = np.bincount(flat[whole], minlength=size)
    out: dict[str, np.ndarray] = {"cell_id": ids, "area_px": counts[ids]}
    out["area_um2"] = counts[ids] * pixel_size_um**2
    out["x_um"] = (np.bincount(flat[whole], weights=cols, minlength=size)[ids] / counts[ids] + 0.5) * pixel_size_um
    out["y_um"] = (np.bincount(flat[whole], weights=rows, minlength=size)[ids] / counts[ids] + 0.5) * pixel_size_um
    del rows, cols
    label_by_condition = {c: flat[s] for c, s in selections.items()}
    for condition, sel in selections.items():
        out[f"pixels__{condition}"] = np.bincount(label_by_condition[condition], minlength=size)[ids]
    for name, image in channels.items():
        values = _read(image).ravel().astype(np.float64)
        for condition, sel in selections.items():
            kept = values[sel]
            lab = label_by_condition[condition]
            out[f"{name}__{condition}__sum"] = np.bincount(lab, weights=kept, minlength=size)[ids]
            out[f"{name}__{condition}__sumsq"] = np.bincount(lab, weights=kept * kept, minlength=size)[ids]
        del values
    return pd.DataFrame(out)


def cell_means(table: pd.DataFrame, channel: str, condition: str) -> pd.Series:
    """Each cell's mean intensity of a channel under a condition; NaN where the condition keeps no pixel."""
    pixels = table[f"pixels__{condition}"].to_numpy(dtype=np.float64)
    sums = table[f"{channel}__{condition}__sum"].to_numpy(dtype=np.float64)
    with np.errstate(invalid="ignore", divide="ignore"):
        return pd.Series(np.where(pixels > 0, sums / pixels, np.nan), index=table.index)


def otsu_threshold(values: np.ndarray) -> float:
    """Otsu's threshold on per-cell means in 0-255: the lower edge of the upper class, from the first split that
    maximises between-class variance."""
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    hist, _ = np.histogram(finite, bins=256, range=(0.0, 256.0))
    centres = np.arange(256, dtype=np.float64)
    weight_low = np.cumsum(hist)[:-1]
    weight_high = hist.sum() - weight_low
    sum_low = np.cumsum(hist * centres)[:-1]
    with np.errstate(invalid="ignore", divide="ignore"):
        mean_low = sum_low / weight_low
        mean_high = ((hist * centres).sum() - sum_low) / weight_high
        between = weight_low * weight_high * (mean_low - mean_high) ** 2
    between = np.where((weight_low > 0) & (weight_high > 0), between, -1.0)
    return float(np.argmax(between) + 1)


def adjacent_pairs(labels: np.ndarray, reach: int = BORDER_REACH_PX) -> np.ndarray:
    """Pairs of cell labels (a < b), sorted, whose pixels lie within `reach` px of each other along a row or column."""
    found = []
    for shift in range(1, reach + 1):
        for a, b in ((labels[:, :-shift], labels[:, shift:]), (labels[:-shift, :], labels[shift:, :])):
            keep = (a > 0) & (b > 0) & (a != b)
            if keep.any():
                pair = np.stack([a[keep], b[keep]], axis=1).astype(np.int64)
                found.append(np.unique(np.sort(pair, axis=1), axis=0))
    if not found:
        return np.zeros((0, 2), dtype=np.int64)
    return np.unique(np.concatenate(found), axis=0)


def positive(table: pd.DataFrame, channel: str, condition: str, threshold: float) -> np.ndarray:
    """Cells whose mean under the condition reaches the threshold; a cell with no pixel kept is not positive."""
    means = cell_means(table, channel, condition).to_numpy()
    return np.where(np.isnan(means), False, means >= threshold)


def random_pixel_loss_probability(table: pd.DataFrame, channel: str, condition: str, threshold: float) -> np.ndarray:
    """Per cell, the probability that a random subset of its pixels as large as the condition keeps has a mean at or
    above the threshold (normal approximation with the finite-population correction)."""
    n = table["pixels__whole_cell"].to_numpy(dtype=np.float64)
    k = table[f"pixels__{condition}"].to_numpy(dtype=np.float64)
    total = table[f"{channel}__whole_cell__sum"].to_numpy(dtype=np.float64)
    total_sq = table[f"{channel}__whole_cell__sumsq"].to_numpy(dtype=np.float64)
    with np.errstate(invalid="ignore", divide="ignore"):
        mu = total / n
        variance = np.maximum(total_sq / n - mu * mu, 0.0)
        mean_variance = np.where((k > 0) & (n > 1), variance / k * (n - k) / (n - 1), 0.0)
        sd = np.sqrt(mean_variance)
        p = np.where(sd > 0, ndtr((mu - threshold) / np.where(sd > 0, sd, 1.0)), (mu >= threshold).astype(np.float64))
    return np.where(k > 0, p, 0.0)


def _in_box(table: pd.DataFrame, roi: Region | None) -> np.ndarray:
    if roi is None:
        return np.ones(len(table), dtype=bool)
    x, y = table["x_um"].to_numpy(), table["y_um"].to_numpy()
    return (x >= roi.x0) & (x < roi.x1) & (y >= roi.y0) & (y < roi.y1)


def _share(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def protein_audit(
    table: pd.DataFrame,
    pairs: np.ndarray,
    *,
    participant_id: str,
    role: str,
    population_marker: str,
    marker: str,
    thresholds: list[ProteinThreshold],
    cell_table_checksum: str,
    roi: Region | None = None,
) -> ProteinAuditResult:
    """The share of `marker`-positive cells among `population_marker`-positive cells, under every measurement
    condition, with its random-pixel-loss expectation, pixel retention and bordering-home shares."""
    limit = {t.marker: t.value for t in thresholds}
    population_all = positive(table, population_marker, "whole_cell", limit[population_marker])
    whole_positive = positive(table, marker, "whole_cell", limit[marker])
    home = whole_positive & ~population_all
    in_scope = _in_box(table, roi) & population_all

    ids = table["cell_id"].to_numpy()
    home_ids = set(ids[home].tolist())
    borders_home_ids: set[int] = set()
    for a, b in pairs.tolist():
        if b in home_ids:
            borders_home_ids.add(a)
        if a in home_ids:
            borders_home_ids.add(b)
    borders_home = np.isin(ids, list(borders_home_ids))

    population_n = int(in_scope.sum())
    whole_pixels = float(table["pixels__whole_cell"].to_numpy()[in_scope].sum())
    rows = []
    for condition in MEASUREMENT_CONDITIONS:
        hit = positive(table, marker, condition, limit[marker]) & in_scope
        p = random_pixel_loss_probability(table, marker, condition, limit[marker])[in_scope]
        kept = float(table[f"pixels__{condition}"].to_numpy()[in_scope].sum())
        excluded = in_scope & whole_positive & ~hit
        retained = in_scope & whole_positive & hit
        reasons = {}
        if not excluded.any():
            reasons["bordering_home_share_excluded"] = "no population cell loses positivity under this condition"
        if not retained.any():
            reasons["bordering_home_share_retained"] = "no population cell stays positive under this condition"
        if population_n == 0:
            reasons["observed_share"] = "no population cell in this scope"
        rows.append(ProteinConditionRow(
            condition=condition,
            positive_cells=int(hit.sum()),
            observed_share=_share(int(hit.sum()), population_n),
            expected_share=float(p.mean()) if population_n else None,
            pixel_retention=kept / whole_pixels if whole_pixels else None,
            excluded_cells=int(excluded.sum()),
            retained_cells=int(retained.sum()),
            bordering_home_share_excluded=_share(int((excluded & borders_home).sum()), int(excluded.sum())),
            bordering_home_share_retained=_share(int((retained & borders_home).sum()), int(retained.sum())),
            reasons=reasons,
        ))

    whole_hits = int((in_scope & whole_positive).sum())
    if population_n < POPULATION_GATE_MIN_CELLS:
        label, reason = EvidenceStatus.INSUFFICIENT_EVIDENCE, f"{population_n} population cells, under the {POPULATION_GATE_MIN_CELLS}-cell population gate"
    elif whole_hits < POSITIVE_GATE_MIN_CELLS:
        label, reason = EvidenceStatus.INSUFFICIENT_EVIDENCE, f"{whole_hits} population cells positive as whole cells, under the {POSITIVE_GATE_MIN_CELLS}-cell gate"
    else:
        drops = [r.condition for r in rows if r.condition in PRIMARY_STRICTER
                 and r.observed_share is not None and r.expected_share is not None
                 and r.observed_share < r.expected_share * THRESHOLD_FACTOR]
        if drops:
            label, reason = EvidenceStatus.SEGMENTATION_SENSITIVE, f"observed share below the random-pixel-loss expectation x 2^-0.5 under {', '.join(drops)}"
        else:
            label, reason = EvidenceStatus.STABLE, "no stricter condition drops the observed share below the random-pixel-loss expectation x 2^-0.5"

    payload = {"participant": participant_id, "population": population_marker, "marker": marker,
               "roi": roi.model_dump(mode="json") if roi else None, "table": cell_table_checksum,
               "thresholds": [t.model_dump(mode="json") for t in thresholds]}
    return ProteinAuditResult(
        result_id=content_id("pra", payload),
        dataset_id=DATASET,
        participant_id=participant_id,
        role=role,
        roi=roi,
        population=f"{population_marker}+ cells",
        population_marker=population_marker,
        marker=marker,
        home=f"{marker}+ cells that are not {population_marker}+",
        population_cells=population_n,
        home_cells=int(home.sum()),
        thresholds=[t for t in thresholds if t.marker in (population_marker, marker)],
        conditions=rows,
        label=label,
        label_reason=reason,
        inference=INFERENCE,
        rules={"threshold": THRESHOLD_RULE, "population": POPULATION_RULE, "home": HOME_RULE, "bordering": BORDER_RULE,
               "expectation": EXPECTATION_RULE, "label": LABEL_RULE, "caveat": CAVEAT},
        cell_table_checksum=cell_table_checksum,
    )
