"""Seam 1: measured depth on a hand-built section whose x, y and z are known by construction.

Podocyte c1 has LRP2 m1 (z 10.2, nuclear), m2 (z 11.7, expansion zone) and m3 (no z); PT cell c2 has LRP2 m4
(z 14.5, nuclear); m5 (NPHS1, unassigned) sits at z 10.9. All but m4 lie in the box x 0..10, y 0..10.
"""

import math

import pandas as pd
import pytest

from spatialscout.contracts import DepthSource, Region
from spatialscout.data import make_section
from spatialscout.engine.depth import DepthJoinError, build_depth_sidecar, depth_points, depth_profile

ROWS = [
    # id, gene, cell, nuclear, x, y, z
    ("m1", "LRP2", "c1", True, 2.0, 2.0, 10.2),
    ("m2", "LRP2", "c1", False, 3.0, 2.5, 11.7),
    ("m3", "LRP2", "c1", True, 2.5, 3.0, math.nan),
    ("m4", "LRP2", "c2", True, 20.0, 20.0, 14.5),
    ("m5", "NPHS1", None, False, 5.0, 5.0, 10.9),
]
BOX = Region(section_id="HAND-Z", x0=0, y0=0, x1=10, y1=10)


@pytest.fixture
def section():
    cells = [
        {"cell_id": "c1", "cell_type": "Podocyte", "x": 2.5, "y": 2.5, "nucleus_area": 28.3, "cell_area": 201.1},
        {"cell_id": "c2", "cell_type": "PT", "x": 20.0, "y": 20.0, "nucleus_area": 28.3, "cell_area": 201.1},
    ]
    molecules = [
        {"molecule_id": i, "gene": g, "cell_id": c, "overlaps_nucleus": n, "nucleus_distance": 0.0 if n else 2.0, "x": x, "y": y, "qv": 40.0}
        for i, g, c, n, x, y, _ in ROWS
    ]
    return make_section(section_id="HAND-Z", dataset_id="hand-built", label_rule_id="hand-built", cells=cells, molecules=molecules)


@pytest.fixture
def raw():
    return pd.DataFrame({"transcript_id": [r[0] for r in ROWS], "x_location": [r[4] for r in ROWS], "y_location": [r[5] for r in ROWS], "z_location": [r[6] for r in ROWS]})


@pytest.fixture
def sidecar(section, raw):
    return build_depth_sidecar(section.molecules, raw)


def source(stats) -> DepthSource:
    return DepthSource(dataset_id="hand-built", section_id="HAND-Z", coordinate_note="test", raw_file="raw", raw_sha256="r", molecules_sha256="m", sidecar_sha256="s", **stats)


def test_the_sidecar_joins_by_id_and_counts_the_missing_depth(sidecar):
    table, stats = sidecar
    assert table["molecule_id"].tolist() == ["m1", "m2", "m3", "m4", "m5"]
    assert (stats["molecules"], stats["with_depth"], stats["missing_depth"]) == (5, 4, 1)
    assert stats["z_min"] == pytest.approx(10.2) and stats["z_max"] == pytest.approx(14.5)


def test_a_join_that_is_not_one_to_one_fails_visibly(section, raw):
    with pytest.raises(DepthJoinError, match="no raw transcript"):
        build_depth_sidecar(section.molecules, raw[raw.transcript_id != "m2"])
    shuffled = raw.assign(x_location=raw.x_location[::-1].to_numpy())
    with pytest.raises(DepthJoinError, match="disagree"):
        build_depth_sidecar(section.molecules, shuffled)


def test_the_profile_counts_every_molecule_in_the_box_by_depth_and_condition(section, sidecar):
    table, stats = sidecar
    profile = depth_profile(section, table, source(stats), BOX, ["LRP2", "NPHS1"], bin_um=1.0)

    assert profile.totals["LRP2"] == {"all": 2, "default": 2, "nucleus_only": 1, "distance_cap_1um": 1, "distance_cap_2um": 2}
    assert profile.missing_depth == {"LRP2": 1, "NPHS1": 0}
    assert profile.totals["NPHS1"]["all"] == 1 and profile.totals["NPHS1"]["default"] == 0
    for gene in profile.genes:
        for condition in profile.conditions:
            assert sum(b.counts[gene][condition] for b in profile.bins) == profile.totals[gene][condition]
    by_bin = {(b.z0, b.z1): b.counts["LRP2"]["all"] for b in profile.bins if b.counts["LRP2"]["all"]}
    assert by_bin == {(10.0, 11.0): 1, (11.0, 12.0): 1}


def test_points_respect_the_depth_slice_and_the_budget_without_changing_counts(section, sidecar):
    table, _ = sidecar
    sliced = depth_points(section, table, BOX, ["LRP2"], (11.0, 12.0), budget=100)
    assert (sliced.total_in_box, sliced.eligible, sliced.displayed) == (3, 1, 1)
    assert sliced.z == [11.7] and sliced.assigned == [True] and sliced.kept_stricter == [False]

    sampled = depth_points(section, table, BOX, ["LRP2", "NPHS1"], None, budget=1)
    assert (sampled.total_in_box, sampled.eligible, sampled.displayed) == (4, 3, 1)


def test_a_sidecar_for_other_molecules_is_refused(section, sidecar):
    table, _ = sidecar
    with pytest.raises(DepthJoinError):
        depth_points(section, table[table.molecule_id != "m1"], BOX, ["LRP2"], None, budget=10)
