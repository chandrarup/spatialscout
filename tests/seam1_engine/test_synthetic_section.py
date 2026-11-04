"""Seam 1: the committed synthetic section SYN-01 and its answers, known by construction.

Construction (scripts/build_synthetic_section.py): 12 cells (3 podocytes, 1 endothelial, 1 mesangial,
4 PT, 2 TAL, 1 T cell). Each cell has 15 molecules over its nucleus and 5 in its expansion zone,
so 240 molecules are assigned; 60 more are unassigned (300 in all). Podocyte C03's 5 expansion-zone
molecules are 1 NPHS1 and 4 LRP2. One glomerulus outline surrounds the 5 glomerular cells.
"""

from pathlib import Path

import pytest

from spatialscout.contracts import ConditionName, EvidenceStatus
from spatialscout.data import DatasetStore
from spatialscout.engine import audit_population, audit_section, label_sensitivity_check

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
DEFAULT = ConditionName.DEFAULT
NUCLEUS_ONLY = ConditionName.NUCLEUS_ONLY


@pytest.fixture(scope="module")
def syn01():
    return DatasetStore(FIXTURES).load_section("SYN-01")


@pytest.fixture(scope="module")
def syn01_audit(syn01):
    return audit_section(syn01, [DEFAULT, NUCLEUS_ONLY])


def test_the_synthetic_section_has_300_molecules_12_labelled_cells_and_one_glomerulus(syn01):
    assert len(syn01.molecules) == 300
    assert syn01.cells["cell_type"].value_counts().to_dict() == {
        "PT": 4, "Podocyte": 3, "TAL": 2, "Endothelial": 1, "Mesangial": 1, "T cell": 1,
    }
    assert [structure.kind for structure in syn01.structures] == ["glomerulus"]


def test_nucleus_only_keeps_180_of_the_240_assigned_molecules(syn01_audit):
    section = syn01_audit.metrics_for(NUCLEUS_ONLY)

    assert (section.default_molecules, section.kept_molecules, section.excluded_molecules) == (240, 180, 60)
    assert section.retention == 0.75


@pytest.mark.parametrize("cell_type", ["Podocyte", "Endothelial", "Mesangial", "PT", "TAL", "T cell"])
def test_every_cell_type_keeps_15_of_every_20_molecules(syn01_audit, cell_type):
    assert syn01_audit.metrics_for(NUCLEUS_ONLY, cell_type=cell_type).retention == 0.75


def test_nucleus_only_excludes_the_lrp2_molecules_in_a_podocytes_expansion_zone(syn01_audit):
    podocyte_lrp2 = syn01_audit.metrics_for(NUCLEUS_ONLY, cell_type="Podocyte", gene="LRP2")

    assert (podocyte_lrp2.default_molecules, podocyte_lrp2.kept_molecules) == (4, 0)


def test_podocyte_nphs1_keeps_the_45_nuclear_molecules_of_56(syn01_audit):
    podocyte_nphs1 = syn01_audit.metrics_for(NUCLEUS_ONLY, cell_type="Podocyte", gene="NPHS1")

    assert (podocyte_nphs1.default_molecules, podocyte_nphs1.kept_molecules) == (56, 45)


@pytest.fixture(scope="module")
def podocyte_lrp2(syn01):
    return audit_population([syn01], cell_type="Podocyte", genes=["LRP2"], conditions=[DEFAULT, NUCLEUS_ONLY])


def test_auditing_podocyte_lrp2_finds_all_four_molecules_outside_the_nucleus(podocyte_lrp2):
    section = podocyte_lrp2.sections[0]
    default, nucleus_only = section.conditions

    assert section.cells_labelled == 3
    assert (default.molecules, default.retention, default.nuclear_overlap_share) == (4, 1.0, 0.0)
    assert default.observed_value == pytest.approx(1 / 3)  # only C03 of the 3 podocytes has LRP2
    assert (nucleus_only.molecules, nucleus_only.retention, nucleus_only.observed_value) == (0, 0.0, 0.0)
    # Every podocyte keeps its 15 nuclear molecules, so all 3 still have a retained molecule of some gene.
    assert nucleus_only.cells_with_retained_molecule == 3


def test_the_one_synthetic_section_is_not_eligible_so_the_result_is_insufficient_evidence(podocyte_lrp2):
    # 3 podocytes and 4 LRP2 molecules: short of the 20 cells and 10 molecules a section needs to be eligible.
    assert podocyte_lrp2.eligible_section_ids == []
    assert podocyte_lrp2.label == EvidenceStatus.INSUFFICIENT_EVIDENCE
    assert podocyte_lrp2.population.label_rule_id == "synthetic-by-construction"


def test_the_home_matched_expectation_uses_lrp2_retention_in_pt_cells(podocyte_lrp2):
    """Each PT cell has 8 nuclear and 3 expansion-zone LRP2 molecules, so LRP2's home-matched retention under
    nucleus-only is 32/44 = 8/11. C03 carries 4 LRP2 molecules: p = 1 - (3/11)^4, over 3 podocytes."""
    nucleus_only = podocyte_lrp2.sections[0].conditions[1]

    assert nucleus_only.expectation_home_matched == pytest.approx((1 - (3 / 11) ** 4) / 3)
    assert nucleus_only.excess_drop_home_matched == pytest.approx((1 - (3 / 11) ** 4) / 3)


def test_the_alternative_label_rule_also_labels_pt_cell_c06_a_podocyte_and_the_check_counts_that_one_cell():
    store = DatasetStore(FIXTURES)
    by_rule = {rule: [store.load_section("SYN-01", rule)] for rule in ("synthetic-by-construction", "synthetic-alternative")}

    check = label_sensitivity_check(by_rule, "Podocyte", ["LRP2"], [DEFAULT, NUCLEUS_ONLY])

    assert store.manifest("synthetic").label_rule_ids == ["synthetic-by-construction", "synthetic-alternative"]
    assert [arm.label_rule_id for arm in check.arms] == ["synthetic-by-construction", "synthetic-alternative"]
    assert [arm.cells_labelled for arm in check.arms] == [3, 4]
    assert (check.cells_in_both, check.cells_only_first, check.cells_only_second) == (3, 0, 1)
