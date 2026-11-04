"""Seam 1: the structure-constrained condition, the exploratory condition built from structure masks (ADR-0006).

A default-condition molecule counts toward its cell under it only when the molecule and the cell's centroid lie on
the same side of every structure outline: both inside the same structure, or both outside all of them.

Hand-built section: one square glomerulus outline over [0, 100] x [0, 100] µm. Cell `in` (centroid at 50, 50) and
cell `out` (centroid at 150, 50). Molecules: two of `in` inside the square, one of `in` outside it (x = 105), one of
`out` inside it (x = 95), two of `out` outside it, and one unassigned. Default keeps the 6 assigned molecules; the
structure-constrained condition keeps the 4 that do not cross the outline.
"""

import pytest

from spatialscout.contracts import ConditionName, EvidenceStatus, StructureMask
from spatialscout.data import make_section
from spatialscout.engine import PRIMARY_CONDITIONS, ConditionUnavailable, audit_population, conditions_for, inclusion_mask

SQUARE = StructureMask(structure_id="g1", section_id="S1", kind="glomerulus", outline=[[0, 0], [100, 0], [100, 100], [0, 100]], source="sam-3.1")


def molecule(i, cell_id, x, y=50.0):
    return {"molecule_id": f"m{i}", "gene": "LRP2", "x": x, "y": y, "cell_id": cell_id, "overlaps_nucleus": False,
            "nucleus_distance": 3.0, "qv": 40.0}


def section(structures=(SQUARE,)):
    return make_section(
        "S1", "test", "full-panel-v1",
        molecules=[
            molecule(0, "in", 40.0), molecule(1, "in", 60.0), molecule(2, "in", 105.0),
            molecule(3, "out", 95.0), molecule(4, "out", 140.0), molecule(5, "out", 160.0),
            molecule(6, None, 50.0),
        ],
        cells=[
            {"cell_id": "in", "cell_type": "Podocyte", "x": 50.0, "y": 50.0, "nucleus_area": 20.0, "cell_area": 60.0},
            {"cell_id": "out", "cell_type": "PT", "x": 150.0, "y": 50.0, "nucleus_area": 20.0, "cell_area": 60.0},
        ],
        structures=structures,
    )


def test_a_molecule_counts_only_on_its_cells_side_of_every_structure_outline():
    kept = inclusion_mask(section(), ConditionName.STRUCTURE_CONSTRAINED)

    assert kept.tolist() == [True, True, False, False, True, True, False]


def test_the_condition_keeps_a_subset_of_the_default_condition():
    s = section()
    default = inclusion_mask(s, ConditionName.DEFAULT)
    kept = inclusion_mask(s, ConditionName.STRUCTURE_CONSTRAINED)

    assert not (kept & ~default).any()


def test_a_section_without_structure_masks_cannot_compute_it_and_does_not_offer_it():
    bare = section(structures=())

    with pytest.raises(ConditionUnavailable):
        inclusion_mask(bare, ConditionName.STRUCTURE_CONSTRAINED)
    assert ConditionName.STRUCTURE_CONSTRAINED not in conditions_for(bare)
    assert ConditionName.STRUCTURE_CONSTRAINED in conditions_for(section())


# --- the exploratory condition never enters an evidence label ----------------------------------------------------


def glomerulus_edge_section(section_id):
    """20 podocytes just inside the square outline, each with 2 LRP2 molecules over its nucleus that lie just outside
    it, so every primary condition keeps them and the structure-constrained condition excludes them all. 20 PT cells
    far outside keep all their LRP2 under every condition, so LRP2's home-matched retention is 1 everywhere."""
    molecules, cells = [], []
    for i in range(20):
        y = 2.0 + 4.8 * i
        cells.append({"cell_id": f"p{i}", "cell_type": "Podocyte", "x": 99.0, "y": y, "nucleus_area": 20.0, "cell_area": 60.0})
        for j in range(2):
            molecules.append({"molecule_id": f"p{i}-{j}", "gene": "LRP2", "x": 101.0, "y": y, "cell_id": f"p{i}",
                              "overlaps_nucleus": True, "nucleus_distance": 0.0, "qv": 40.0})
        cells.append({"cell_id": f"t{i}", "cell_type": "PT", "x": 300.0, "y": y, "nucleus_area": 20.0, "cell_area": 60.0})
        for j in range(3):
            molecules.append({"molecule_id": f"t{i}-{j}", "gene": "LRP2", "x": 300.0, "y": y, "cell_id": f"t{i}",
                              "overlaps_nucleus": True, "nucleus_distance": 0.0, "qv": 40.0})
    square = SQUARE.model_copy(update={"section_id": section_id})
    return make_section(section_id, "test", "full-panel-v1", molecules=molecules, cells=cells, structures=[square])


def test_adding_or_removing_the_exploratory_condition_changes_no_evidence_label():
    sections = [glomerulus_edge_section(f"S{i}") for i in range(1, 4)]

    without = audit_population(sections, "Podocyte", ["LRP2"], PRIMARY_CONDITIONS)
    with_it = audit_population(sections, "Podocyte", ["LRP2"], [*PRIMARY_CONDITIONS, ConditionName.STRUCTURE_CONSTRAINED])

    assert without.label == with_it.label == EvidenceStatus.STABLE
    assert with_it.label_reason == without.label_reason
    assert with_it.leave_one_section_out == without.leave_one_section_out
    assert with_it.sections == without.sections and with_it.pooled == without.pooled
    # The exploratory values are computed, kept apart, and would have flipped the label had they counted:
    # every podocyte loses its LRP2 while LRP2's home-matched expectation stays at 1.
    assert [s.section_id for s in with_it.exploratory_sections] == ["S1", "S2", "S3"]
    for values in with_it.exploratory_sections:
        (row,) = values.conditions
        assert row.condition == ConditionName.STRUCTURE_CONSTRAINED
        assert (row.molecules, row.observed_value, row.expectation_home_matched) == (0, 0.0, 1.0)


def test_sections_without_structure_masks_are_left_out_of_the_exploratory_values_only():
    sections = [glomerulus_edge_section("S1"), glomerulus_edge_section("S2"), glomerulus_edge_section("S3")]
    sections[2] = make_section("S3", "test", "full-panel-v1", molecules=sections[2].molecules, cells=sections[2].cells)

    result = audit_population(sections, "Podocyte", ["LRP2"], [*PRIMARY_CONDITIONS, ConditionName.STRUCTURE_CONSTRAINED])

    assert [s.section_id for s in result.sections] == ["S1", "S2", "S3"]
    assert [s.section_id for s in result.exploratory_sections] == ["S1", "S2"]
