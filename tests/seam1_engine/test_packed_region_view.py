"""Seam 1: the packed region view, decoded back from its typed little-endian columns on a hand-built section.

Section: 2 cells (c1 a Podocyte with a nucleus of area 4*pi, so radius 2; c2 a PT cell with no detected nucleus)
and 4 molecules: NPHS1 over c1's nucleus, LRP2 in c1's expansion zone, UMOD over c2's nucleus, and an unassigned
LRP2. Default keeps the 3 assigned molecules; nucleus-only keeps the 2 over a nucleus.
"""

import base64
import math

import numpy as np
import pytest

from spatialscout.contracts import ConditionName
from spatialscout.data import make_section
from spatialscout.engine import build_packed_region_view


def decode(column):
    return np.frombuffer(base64.b64decode(column.data), dtype=np.dtype(column.dtype).newbyteorder("<"))


@pytest.fixture(scope="module")
def view():
    def molecule(i, gene, cell_id, x, overlaps):
        return {"molecule_id": str(i), "gene": gene, "x": x, "y": 10.5, "cell_id": cell_id, "overlaps_nucleus": overlaps,
                "nucleus_distance": 0.0 if overlaps else 1.5, "qv": 40.0}

    section = make_section(
        "S1", "test", "full-panel-v1",
        molecules=[
            molecule(0, "NPHS1", "c1", 1.25, True),
            molecule(1, "LRP2", "c1", 2.5, False),
            molecule(2, "UMOD", "c2", 30.0, True),
            molecule(3, "LRP2", None, 40.0, False),
        ],
        cells=[
            {"cell_id": "c1", "cell_type": "Podocyte", "x": 1.0, "y": 10.0, "nucleus_area": 4 * math.pi, "cell_area": 30.0},
            {"cell_id": "c2", "cell_type": "PT", "x": 30.0, "y": 11.0, "nucleus_area": math.nan, "cell_area": 30.0},
        ],
    )
    return build_packed_region_view(section, [ConditionName.DEFAULT, ConditionName.NUCLEUS_ONLY], synthetic=False)


def test_molecule_positions_genes_and_cells_decode_exactly(view):
    m = view.molecules

    assert decode(m.x).tolist() == [1.25, 2.5, 30.0, 40.0]
    assert decode(m.y).tolist() == [10.5] * 4
    assert [view.genes[i] for i in decode(m.gene_index)] == ["NPHS1", "LRP2", "UMOD", "LRP2"]
    assert decode(m.cell_index).tolist() == [0, 0, 1, -1]


def test_each_condition_owns_one_inclusion_bit(view):
    bits = decode(view.molecules.inclusion_bits)
    kept = {c: ((bits >> b) & 1).tolist() for c, b in view.molecules.condition_bits.items()}

    assert kept == {"default": [1, 1, 1, 0], "nucleus_only": [1, 0, 1, 0]}


def test_cells_carry_their_label_and_a_nucleus_radius_or_zero_without_a_nucleus(view):
    c = view.cells

    assert c.cell_id == ["c1", "c2"]
    assert [view.cell_types[i] for i in decode(c.cell_type_index)] == ["Podocyte", "PT"]
    assert decode(c.nucleus_radius).tolist() == [2.0, 0.0]
    assert (decode(c.x).tolist(), decode(c.y).tolist()) == ([1.0, 30.0], [10.0, 11.0])
