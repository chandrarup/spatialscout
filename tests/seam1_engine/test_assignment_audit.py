"""Seam 1: the assignment audit on tiny hand-built tables whose answers are known by construction."""

import pytest

from spatialscout.contracts import ConditionName
from spatialscout.data import make_section
from spatialscout.engine import audit_section

DEFAULT = ConditionName.DEFAULT
NUCLEUS_ONLY = ConditionName.NUCLEUS_ONLY


def cell(cell_id: str, cell_type: str) -> dict:
    return {"cell_id": cell_id, "cell_type": cell_type, "x": 0.0, "y": 0.0, "nucleus_area": 28.3, "cell_area": 201.1}


def molecule(molecule_id: str, gene: str, cell_id: str | None, overlaps_nucleus: bool) -> dict:
    return {
        "molecule_id": molecule_id,
        "gene": gene,
        "cell_id": cell_id,
        "overlaps_nucleus": overlaps_nucleus,
        "nucleus_distance": 0.0 if overlaps_nucleus else 2.0,
        "x": 0.0,
        "y": 0.0,
        "qv": 40.0,
    }


@pytest.fixture
def podocyte_with_expansion_zone_molecule():
    """A podocyte (c1) with two nuclear NPHS1 molecules and one LRP2 molecule in its expansion zone,
    a proximal-tubule cell (c2) with one nuclear LRP2 molecule, an unassigned CUBN molecule,
    and a T cell (c3) with no molecules."""
    return make_section(
        section_id="HAND-1",
        dataset_id="hand-built",
        cells=[cell("c1", "Podocyte"), cell("c2", "PT"), cell("c3", "T cell")],
        molecules=[
            molecule("m1", "NPHS1", "c1", overlaps_nucleus=True),
            molecule("m2", "NPHS1", "c1", overlaps_nucleus=True),
            molecule("m3", "LRP2", "c1", overlaps_nucleus=False),
            molecule("m4", "LRP2", "c2", overlaps_nucleus=True),
            molecule("m5", "CUBN", None, overlaps_nucleus=False),
        ],
    )


def test_nucleus_only_excludes_a_molecule_in_a_podocytes_expansion_zone(podocyte_with_expansion_zone_molecule):
    audit = audit_section(podocyte_with_expansion_zone_molecule, [DEFAULT, NUCLEUS_ONLY])

    assert audit.excluded_molecule_ids[NUCLEUS_ONLY] == ["m3"]


def test_section_retention_counts_only_molecules_assigned_under_the_default_condition(podocyte_with_expansion_zone_molecule):
    audit = audit_section(podocyte_with_expansion_zone_molecule, [DEFAULT, NUCLEUS_ONLY])

    section = audit.metrics_for(NUCLEUS_ONLY)
    # m1..m4 are assigned (m5 is not); nucleus-only keeps m1, m2 and m4.
    assert (section.default_molecules, section.kept_molecules, section.excluded_molecules) == (4, 3, 1)
    assert section.retention == pytest.approx(0.75)


def test_retention_by_cell_type_and_by_gene_within_a_cell_type(podocyte_with_expansion_zone_molecule):
    audit = audit_section(podocyte_with_expansion_zone_molecule, [DEFAULT, NUCLEUS_ONLY])

    assert audit.metrics_for(NUCLEUS_ONLY, cell_type="Podocyte").retention == pytest.approx(2 / 3)
    assert audit.metrics_for(NUCLEUS_ONLY, cell_type="Podocyte", gene="LRP2").retention == 0.0
    assert audit.metrics_for(NUCLEUS_ONLY, cell_type="PT").retention == 1.0


def test_the_default_condition_keeps_every_assigned_molecule(podocyte_with_expansion_zone_molecule):
    audit = audit_section(podocyte_with_expansion_zone_molecule, [DEFAULT, NUCLEUS_ONLY])

    assert audit.metrics_for(DEFAULT).retention == 1.0
    assert audit.excluded_molecule_ids[DEFAULT] == []


def test_a_cell_type_without_molecules_has_no_retention_and_says_why(podocyte_with_expansion_zone_molecule):
    audit = audit_section(podocyte_with_expansion_zone_molecule, [DEFAULT, NUCLEUS_ONLY])

    t_cells = audit.metrics_for(NUCLEUS_ONLY, cell_type="T cell")
    assert (t_cells.default_molecules, t_cells.retention) == (0, None)
    assert t_cells.retention_missing_reason
