"""Seam 1: validating one raw GSE286184 section into molecule and cell tables.

The raw tables below are hand-built in the GEO deposit's own column names. Every record that does not reach
the validated tables is counted under a named reason, so nothing is dropped silently.
"""

import math

import pandas as pd
import pytest

from spatialscout.data import MalformedSection, validate_section

PANEL = ["LRP2", "NPHS1", "UMOD"]


def transcript(transcript_id, gene, cell_id="c1", x=1.0, y=2.0, qv=40.0, overlaps_nucleus=1, nucleus_distance=0.0):
    return {
        "transcript_id": transcript_id, "cell_id": cell_id, "overlaps_nucleus": overlaps_nucleus, "feature_name": gene,
        "x_location": x, "y_location": y, "qv": qv, "nucleus_distance": nucleus_distance,
    }


def cell(cell_id, x=1.0, y=2.0, nucleus_area=12.0, cell_area=40.0):
    return {"cell_id": cell_id, "x_centroid": x, "y_centroid": y, "nucleus_area": nucleus_area, "cell_area": cell_area}


RAW_TRANSCRIPTS = pd.DataFrame([
    transcript(1, "NPHS1"),                              # kept, assigned to c1
    transcript(2, "LRP2", cell_id="UNASSIGNED"),         # kept, unassigned
    transcript(3, "UMOD", cell_id="c9"),                 # kept, but c9 is not in the cells table: unmatched
    transcript(4, "NPHS1", qv=12.5),                     # below the quality threshold
    transcript(5, "NegControlProbe_00042"),              # not a panel gene
    transcript(6, "LRP2", x=math.nan),                   # malformed: no position
    transcript(7, "LRP2", overlaps_nucleus=3),           # malformed: the nucleus flag is not 0 or 1
    transcript(8, None),                                 # malformed: no gene
    transcript(1, "UMOD"),                               # duplicate transcript id
])
RAW_CELLS = pd.DataFrame([cell("c1"), cell("c2"), cell("c4", nucleus_area=math.nan), cell("c3", x=math.inf), cell("c1", x=5.0)])


@pytest.fixture(scope="module")
def validated():
    return validate_section(RAW_TRANSCRIPTS, RAW_CELLS, PANEL)


def test_every_raw_molecule_is_kept_or_counted_under_one_reason(validated):
    counts = validated.validation

    assert (counts.molecules_read, counts.molecules_kept) == (9, 3)
    assert (counts.malformed_molecules, counts.duplicate_molecules) == (3, 1)
    assert (counts.below_quality, counts.not_in_panel) == (1, 1)


def test_an_unmatched_molecule_is_counted_and_kept_as_unassigned(validated):
    counts = validated.validation
    molecules = validated.molecules.set_index("molecule_id")

    assert (counts.unassigned_molecules, counts.unmatched_molecules) == (1, 1)
    assert pd.isna(molecules.loc["3", "cell_id"]) and pd.isna(molecules.loc["2", "cell_id"])
    assert molecules.loc["1", "cell_id"] == "c1"


def test_malformed_and_duplicate_cells_are_counted_and_cells_without_molecules_or_a_nucleus_kept(validated):
    counts = validated.validation

    assert (counts.cells_read, counts.malformed_cells, counts.duplicate_cells, counts.cells_kept) == (5, 1, 1, 3)
    assert (counts.cells_without_molecules, counts.cells_without_nucleus) == (2, 1)
    assert sorted(validated.cells["cell_id"]) == ["c1", "c2", "c4"]


def test_the_validated_tables_use_glossary_columns(validated):
    molecule = validated.molecules.set_index("molecule_id").loc["1"]

    assert (molecule["gene"], molecule["x"], molecule["y"], bool(molecule["overlaps_nucleus"])) == ("NPHS1", 1.0, 2.0, True)
    assert list(validated.cells.columns[:3]) == ["cell_id", "x", "y"]


def test_a_section_missing_a_required_column_is_refused():
    with pytest.raises(MalformedSection, match="nucleus_distance"):
        validate_section(RAW_TRANSCRIPTS.drop(columns=["nucleus_distance"]), RAW_CELLS, PANEL)
