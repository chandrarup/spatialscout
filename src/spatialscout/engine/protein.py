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

MEASUREMENT_CONDITIONS = ("whole_cell", "eroded_1px", "eroded_2px", "nucleus_region")
PRIMARY_STRICTER = ("eroded_1px", "eroded_2px", "nucleus_region")

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
