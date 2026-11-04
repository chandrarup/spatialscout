"""Seam 1: the rendered channels of a section, which the dual viewer draws as a multichannel image.

Section: 3 cells (c1 a Podocyte with a nucleus, c2 a PT cell with a nucleus, c3 a TAL cell with no detected
nucleus) and 7 molecules: 2 NPHS1 in c1, 1 LRP2 and 2 CUBN in c2, 1 UMOD in c3 and 1 unassigned UMOD. No CD3D,
CD8A, MS4A1 or POSTN molecule exists. Every channel draws every molecule of its genes, assigned or not, so the
expected counts come straight from that list: NPHS1 2, LRP2/CUBN 3, UMOD 2, nuclei 2 (c3 has none).
"""

import math

import pytest

from spatialscout.data import make_section
from spatialscout.engine import section_channels


@pytest.fixture(scope="module")
def section():
    def molecule(i, gene, cell_id, x):
        return {"molecule_id": str(i), "gene": gene, "x": x, "y": 5.0, "cell_id": cell_id, "overlaps_nucleus": True,
                "nucleus_distance": 0.0, "qv": 40.0}

    def cell(cell_id, cell_type, x, nucleus_area):
        return {"cell_id": cell_id, "cell_type": cell_type, "x": x, "y": 5.0, "nucleus_area": nucleus_area, "cell_area": 40.0}

    return make_section(
        "S1", "test", "full-panel-v1",
        molecules=[
            molecule(0, "NPHS1", "c1", 1.0),
            molecule(1, "NPHS1", "c1", 2.0),
            molecule(2, "LRP2", "c2", 20.0),
            molecule(3, "CUBN", "c2", 21.0),
            molecule(4, "CUBN", "c2", 22.0),
            molecule(5, "UMOD", "c3", 40.0),
            molecule(6, "UMOD", None, 60.0),
        ],
        cells=[
            cell("c1", "Podocyte", 1.5, 4 * math.pi),
            cell("c2", "PT", 21.0, 9 * math.pi),
            cell("c3", "TAL", 40.0, math.nan),
        ],
    )


def test_the_six_channels_are_listed_in_their_frozen_order_with_their_genes(section):
    channels = section_channels(section).channels

    assert [(c.channel_id, c.genes) for c in channels] == [
        ("nuclei", []),
        ("nphs1", ["NPHS1"]),
        ("lrp2_cubn", ["LRP2", "CUBN"]),
        ("umod", ["UMOD"]),
        ("lymphocyte", ["CD3D", "CD8A", "MS4A1"]),
        ("postn", ["POSTN"]),
    ]


def test_each_channel_counts_every_molecule_of_its_genes_assigned_or_not(section):
    counts = {c.channel_id: c.count for c in section_channels(section).channels}

    assert counts == {"nuclei": 2, "nphs1": 2, "lrp2_cubn": 3, "umod": 2, "lymphocyte": 0, "postn": 0}


def test_a_channel_with_no_molecules_of_its_genes_is_unavailable_with_a_reason_not_an_error(section):
    channels = {c.channel_id: c for c in section_channels(section).channels}

    assert channels["postn"].available is False
    assert channels["postn"].missing_genes == ["POSTN"]
    assert "POSTN" in (channels["postn"].unavailable_reason or "")
    assert channels["lrp2_cubn"].available is True and channels["lrp2_cubn"].missing_genes == []


def test_the_channel_set_states_it_is_rendered_from_molecules_and_where_nuclei_come_from(section):
    channel_set = section_channels(section)

    assert channel_set.section_id == "S1"
    assert channel_set.provenance == "rendered from molecules"
    nuclei = channel_set.channels[0]
    assert nuclei.source == "nuclei" and "nucleus" in nuclei.description.lower()
    assert all(c.source == "molecules" for c in channel_set.channels[1:])
