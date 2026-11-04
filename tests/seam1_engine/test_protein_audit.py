"""Seam 1: the protein-level audit on KPMP CODEX images (ticket 02c): per-cell measurements under the four
measurement conditions, positivity, the random-pixel-loss expectations, neighbour proximity and the evidence label,
on tiny hand-built masks and images whose answers are worked out by hand in each docstring."""

import math

import numpy as np
import pytest

from spatialscout.engine.protein import (
    MEASUREMENT_CONDITIONS,
    cell_means,
    channel_index_by_marker,
    measure_cells,
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
