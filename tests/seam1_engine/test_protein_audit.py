"""Seam 1: the protein-level audit on KPMP CODEX images (ticket 02c): per-cell measurements under the four
measurement conditions, positivity, the random-pixel-loss expectations, neighbour proximity and the evidence label,
on tiny hand-built masks and images whose answers are worked out by hand in each docstring."""

import math

import numpy as np
import pytest

import pandas as pd

from spatialscout.contracts import ProteinThreshold, Region
from spatialscout.engine.protein import (
    MEASUREMENT_CONDITIONS,
    adjacent_pairs,
    cell_means,
    channel_index_by_marker,
    measure_cells,
    otsu_threshold,
    protein_audit,
    random_pixel_loss_probability,
)

PX = 0.5  # µm per pixel in these hand-built images


def two_cells():
    """A 7 x 10 image with two cells.

    Cell 1: rows 1-5, cols 1-5 (25 px). Its marker is 10 on the 16-pixel ring, 50 on the inner ring of 8 and 90 at
    the centre (3, 3); DAPI is 200 on the inner 3 x 3 and 5 elsewhere.
    Cell 2: rows 1-3, cols 7-8 (6 px). Its marker is 20 everywhere; DAPI is 200 only at (2, 7).
    """
    labels = np.zeros((7, 10), dtype=np.int32)
    labels[1:6, 1:6] = 1
    labels[1:4, 7:9] = 2
    marker = np.zeros((7, 10), dtype=np.uint8)
    marker[1:6, 1:6] = 10
    marker[2:5, 2:5] = 50
    marker[3, 3] = 90
    marker[1:4, 7:9] = 20
    dapi = np.full((7, 10), 5, dtype=np.uint8)
    dapi[2:5, 2:5] = 200
    dapi[2, 7] = 200
    return labels, marker, dapi


def test_every_per_cell_measurement_on_a_hand_built_mask():
    """Area: 25 px = 6.25 µm² and 6 px = 1.5 µm². Centroids at pixel centres: cell 1 (row 3, col 3) is at
    x = y = 3.5 x 0.5 = 1.75 µm; cell 2 (row 2, col 7.5) is at x = 4.0, y = 1.25 µm.

    Whole cell: cell 1 = (16 x 10 + 8 x 50 + 90) / 25 = 26; cell 2 = 20.
    Eroded 1 px (a pixel whose 3 x 3 neighbourhood is all its own cell): cell 1 keeps its inner 3 x 3,
    (8 x 50 + 90) / 9 = 54.44; cell 2 is 2 px wide, so nothing is left and it has no value.
    Eroded 2 px (5 x 5 neighbourhood): cell 1 keeps only its centre, 90; cell 2 nothing.
    Nucleus region (DAPI >= 100 inside the cell): cell 1's inner 3 x 3 again, 54.44; cell 2's one pixel, 20.
    """
    labels, marker, dapi = two_cells()
    table = measure_cells(labels, {"M": marker}, dapi=dapi, nucleus_threshold=100, pixel_size_um=PX)

    assert list(table["cell_id"]) == [1, 2]
    assert list(table["area_px"]) == [25, 6]
    assert table["area_um2"].tolist() == pytest.approx([6.25, 1.5])
    assert table["x_um"].tolist() == pytest.approx([1.75, 4.0])
    assert table["y_um"].tolist() == pytest.approx([1.75, 1.25])

    assert cell_means(table, "M", "whole_cell").tolist() == pytest.approx([26.0, 20.0])
    eroded_1 = cell_means(table, "M", "eroded_1px").tolist()
    assert eroded_1[0] == pytest.approx(490 / 9) and math.isnan(eroded_1[1])
    eroded_2 = cell_means(table, "M", "eroded_2px").tolist()
    assert eroded_2[0] == pytest.approx(90.0) and math.isnan(eroded_2[1])
    assert cell_means(table, "M", "nucleus_region").tolist() == pytest.approx([490 / 9, 20.0])

    assert list(table["pixels__whole_cell"]) == [25, 6]
    assert list(table["pixels__eroded_1px"]) == [9, 0]
    assert list(table["pixels__eroded_2px"]) == [1, 0]
    assert list(table["pixels__nucleus_region"]) == [9, 1]
    assert set(MEASUREMENT_CONDITIONS) == {"whole_cell", "eroded_1px", "eroded_2px", "nucleus_region"}


def test_a_cell_touching_the_image_edge_erodes_from_the_edge():
    """A 3 x 3 cell in the image corner: outside the image counts as background, so 1 px erosion leaves only (1, 1)."""
    labels = np.zeros((4, 4), dtype=np.int32)
    labels[0:3, 0:3] = 7
    marker = np.arange(16, dtype=np.uint8).reshape(4, 4)
    table = measure_cells(labels, {"M": marker}, dapi=marker, nucleus_threshold=255, pixel_size_um=1.0)
    assert list(table["pixels__eroded_1px"]) == [1]
    assert cell_means(table, "M", "eroded_1px").tolist() == pytest.approx([5.0])


def test_channels_are_found_by_marker_name_not_position():
    """The two KPMP panels order their channels differently: CD31 is channel 29 in 23-0118 and 32 in 23-0159."""
    key_0118 = "Channel,Marker\n1,DAPI\n29,CD31\n42,UMOD\n"
    key_0159 = "﻿Channel,Marker\n1,DAPI\n32,CD31\n45,UMOD\n"
    assert channel_index_by_marker(key_0118) == {"DAPI": 0, "CD31": 28, "UMOD": 41}
    assert channel_index_by_marker(key_0159) == {"DAPI": 0, "CD31": 31, "UMOD": 44}


def test_otsu_threshold_splits_two_groups_of_cell_means():
    """Means of 10 and 200, fifty each: every split between them separates the groups equally well, and the rule
    takes the first, so the threshold is 11 (the class at or above it holds the 200s)."""
    values = np.array([10.0] * 50 + [200.0] * 50)
    assert otsu_threshold(values) == 11.0


def test_cells_separated_by_a_one_pixel_gap_border_each_other():
    """Cells 1 and 2 are one background pixel apart, so they border (reach 2 px); cell 3 is four pixels from cell 2."""
    labels = np.zeros((3, 12), dtype=np.int32)
    labels[:, 0:3] = 1
    labels[:, 4:6] = 2
    labels[:, 10:12] = 3
    assert adjacent_pairs(labels).tolist() == [[1, 2]]


def single_channel_table(n: int, kept: int, total: float, total_sq: float, kept_sum: float) -> pd.DataFrame:
    row = {"cell_id": 1, "x_um": 0.0, "y_um": 0.0, "pixels__whole_cell": n, "pixels__eroded_1px": kept,
           "M__whole_cell__sum": total, "M__whole_cell__sumsq": total_sq, "M__eroded_1px__sum": kept_sum}
    return pd.DataFrame([row])


def test_random_pixel_loss_probability_in_closed_form():
    """A 4-pixel cell with values 0, 0, 10, 10: mean 5 and population variance 25. Keeping 2 random pixels, the kept
    mean has variance 25 / 2 x (4 - 2) / (4 - 1) = 8.33 around 5, so it reaches a threshold of 5 with probability
    0.5 and a threshold of 5 + sqrt(8.33) with probability 1 - Phi(1) = 0.1587. Keeping no pixel gives 0."""
    table = single_channel_table(4, 2, 20.0, 200.0, 10.0)
    assert random_pixel_loss_probability(table, "M", "eroded_1px", 5.0)[0] == pytest.approx(0.5)
    assert random_pixel_loss_probability(table, "M", "eroded_1px", 5.0 + math.sqrt(25 / 3))[0] == pytest.approx(0.158655, abs=1e-5)
    assert random_pixel_loss_probability(table, "M", "whole_cell", 5.0)[0] == 1.0
    assert random_pixel_loss_probability(single_channel_table(4, 0, 20.0, 200.0, 0.0), "M", "eroded_1px", 5.0)[0] == 0.0


def audit_table() -> tuple[pd.DataFrame, np.ndarray]:
    """25 population cells (P = 200) and 5 home cells (P = 0, M = 100), every cell 10 px of uniform intensity.

    - Cells 1-10 (x = 1..10 µm): M = 100 as whole cells, but their 5 eroded pixels hold no M. Each borders a home cell.
    - Cells 11-20 (x = 101..110 µm): M = 100 everywhere, 5 eroded pixels kept. They border nothing.
    - Cells 21-25 (x = 201..205 µm): no M.
    Eroded 2 px and nucleus region keep every pixel, so nothing changes under them.
    """
    rows = []
    for cell in range(1, 31):
        population = cell <= 25
        m_whole = 100.0 if cell <= 20 or cell > 25 else 0.0
        m_eroded = 0.0 if cell <= 10 else m_whole
        x = {0: 1.0, 1: 101.0, 2: 201.0}[(cell - 1) // 10] + (cell - 1) % 10 if population else 500.0 + cell
        row = {"cell_id": cell, "x_um": x, "y_um": 5.0, "pixels__whole_cell": 10, "pixels__eroded_1px": 5,
               "pixels__eroded_2px": 10, "pixels__nucleus_region": 10}
        for channel, whole, eroded in (("P", 200.0 if population else 0.0, 200.0 if population else 0.0), ("M", m_whole, m_eroded)):
            for condition, pixels, value in (("whole_cell", 10, whole), ("eroded_1px", 5, eroded), ("eroded_2px", 10, whole), ("nucleus_region", 10, whole)):
                row[f"{channel}__{condition}__sum"] = value * pixels
                row[f"{channel}__{condition}__sumsq"] = value * value * pixels
        rows.append(row)
    pairs = np.array([[cell, 26 + (cell - 1) % 5] for cell in range(1, 11)])
    return pd.DataFrame(rows), pairs


THRESHOLDS = [ProteinThreshold(marker=m, value=50.0, rule="test", source_participant_id="ref") for m in ("P", "M")]


def test_protein_audit_reports_observed_expected_retention_and_bordering_shares():
    """Eroded 1 px: 10 of 25 population cells stay M+ (0.4). Every whole-cell M+ cell has zero variance and keeps
    pixels, so the random-pixel-loss expectation is 20 / 25 = 0.8. Retention 125 / 250 = 0.5. The 10 excluded cells
    all border a home cell, the 10 retained cells none. 0.4 < 0.8 x 2^-0.5, so the result is segmentation-sensitive."""
    table, pairs = audit_table()
    result = protein_audit(table, pairs, participant_id="p1", role="diseased", population_marker="P", marker="M",
                           thresholds=THRESHOLDS, cell_table_checksum="abc")
    rows = {r.condition: r for r in result.conditions}
    assert result.population_cells == 25 and result.home_cells == 5
    assert rows["whole_cell"].observed_share == pytest.approx(0.8) and rows["whole_cell"].expected_share == pytest.approx(0.8)
    eroded = rows["eroded_1px"]
    assert (eroded.positive_cells, eroded.observed_share, eroded.expected_share) == (10, pytest.approx(0.4), pytest.approx(0.8))
    assert eroded.pixel_retention == pytest.approx(0.5)
    assert (eroded.excluded_cells, eroded.retained_cells) == (10, 10)
    assert (eroded.bordering_home_share_excluded, eroded.bordering_home_share_retained) == (1.0, 0.0)
    assert rows["nucleus_region"].excluded_cells == 0 and rows["nucleus_region"].bordering_home_share_excluded is None
    assert result.label.value == "segmentation_sensitive"
    assert result.population == "P+ cells" and result.home == "M+ cells that are not P+"


def test_a_region_with_too_few_population_cells_is_insufficient_evidence():
    """A box around cells 11-20 holds 10 population cells, under the 20-cell population gate."""
    table, pairs = audit_table()
    box = Region(section_id="p1", x0=100.0, y0=0.0, x1=120.0, y1=10.0)
    result = protein_audit(table, pairs, participant_id="p1", role="diseased", population_marker="P", marker="M",
                           thresholds=THRESHOLDS, cell_table_checksum="abc", roi=box)
    assert result.population_cells == 10
    assert result.label.value == "insufficient_evidence"
    assert "20" in result.label_reason
    assert result.roi == box
