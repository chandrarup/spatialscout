"""Seam 1: random-thinning expectations, co-expression, neighbour proximity, evidence regions and audit labels,
on tiny hand-built tables whose answers are worked out by hand in each docstring."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from spatialscout.contracts import ConditionName, EvidenceStatus, Region
from spatialscout.data import make_section
from spatialscout.engine import audit_population, gate_status, label_sensitivity_check, load_marker_pairs

DEFAULT = ConditionName.DEFAULT
NUCLEUS_ONLY = ConditionName.NUCLEUS_ONLY
REPO = Path(__file__).resolve().parents[2]


def cell(cell_id, cell_type, x=0.0, y=0.0):
    return {"cell_id": cell_id, "cell_type": cell_type, "x": x, "y": y, "nucleus_area": 28.3, "cell_area": 201.1}


def mol(molecule_id, gene, cell_id, nuclear, x=0.0, y=0.0):
    return {
        "molecule_id": molecule_id,
        "gene": gene,
        "cell_id": cell_id,
        "overlaps_nucleus": nuclear,
        "nucleus_distance": 0.0 if nuclear else 5.0,
        "x": x,
        "y": y,
        "qv": 40.0,
    }


def section(section_id, cells, molecules):
    return make_section(section_id=section_id, dataset_id="hand-built", label_rule_id="hand-built", cells=cells, molecules=molecules)


def by_condition(values):
    return {v.condition: v for v in values.conditions}


@pytest.fixture
def podocytes_with_lrp2_or_cubn():
    """Five podocytes and one PT cell.

    - p1: LRP2 x2 (one nuclear), NPHS1 x3 nuclear. Retention under nucleus-only 4/5.
    - p2: CUBN x1 outside the nucleus, NPHS1 x1 nuclear. Retention 1/2.
    - p3: NPHS1 x1 nuclear. p4: no molecules. p5: NPHS1 x1 outside the nucleus (zero retention).
    - pt1, the home cell type of LRP2 and CUBN: LRP2 x4 (3 nuclear), CUBN x2 (1 nuclear), so the home-matched
      retentions are 0.75 for LRP2 and 0.5 for CUBN.

    LRP2 or CUBN present: default p1, p2 = 2/5; nucleus-only p1 = 1/5.
    Home-matched: p1 1 - 0.25^2 = 0.9375, p2 1 - 0.5 = 0.5 -> (0.9375 + 0.5) / 5 = 0.2875.
    Cell-matched: p1 1 - 0.2^2 = 0.96, p2 1 - 0.5 = 0.5 -> (0.96 + 0.5) / 5 = 0.292.
    """
    cells = [cell(f"p{i}", "Podocyte") for i in range(1, 6)] + [cell("pt1", "PT")]
    molecules = [
        mol("a1", "LRP2", "p1", True), mol("a2", "LRP2", "p1", False),
        mol("a3", "NPHS1", "p1", True), mol("a4", "NPHS1", "p1", True), mol("a5", "NPHS1", "p1", True),
        mol("b1", "CUBN", "p2", False), mol("b2", "NPHS1", "p2", True),
        mol("c1", "NPHS1", "p3", True),
        mol("e1", "NPHS1", "p5", False),
        mol("t1", "LRP2", "pt1", True), mol("t2", "LRP2", "pt1", True), mol("t3", "LRP2", "pt1", True), mol("t4", "LRP2", "pt1", False),
        mol("t5", "CUBN", "pt1", True), mol("t6", "CUBN", "pt1", False),
    ]
    return section("HAND-HERO", cells, molecules)


def test_gene_set_presence_and_both_thinning_expectations_match_the_worked_example(podocytes_with_lrp2_or_cubn):
    result = audit_population([podocytes_with_lrp2_or_cubn], "Podocyte", ["LRP2", "CUBN"], [DEFAULT, NUCLEUS_ONLY])

    values = by_condition(result.sections[0])
    assert result.measure == "gene_set_share_expressing"
    assert values[DEFAULT].observed_value == pytest.approx(2 / 5)
    assert values[NUCLEUS_ONLY].observed_value == pytest.approx(1 / 5)
    assert values[NUCLEUS_ONLY].expectation_home_matched == pytest.approx(0.2875)
    assert values[NUCLEUS_ONLY].expectation_cell_matched == pytest.approx(0.292)
    assert values[NUCLEUS_ONLY].excess_drop_home_matched == pytest.approx(0.2875 - 0.2)
    assert values[NUCLEUS_ONLY].excess_drop_cell_matched == pytest.approx(0.292 - 0.2)
    # Under the default condition nothing is thinned, so both expectations equal the observed value.
    assert values[DEFAULT].expectation_home_matched == pytest.approx(2 / 5)
    assert values[DEFAULT].expectation_cell_matched == pytest.approx(2 / 5)


def test_retention_counts_the_results_molecules_in_the_population(podocytes_with_lrp2_or_cubn):
    result = audit_population([podocytes_with_lrp2_or_cubn], "Podocyte", ["LRP2", "CUBN"], [DEFAULT, NUCLEUS_ONLY])

    nucleus_only = by_condition(result.sections[0])[NUCLEUS_ONLY]
    # a1, a2, b1 under the default condition; only a1 is nuclear.
    assert (nucleus_only.molecules, nucleus_only.retention) == (1, pytest.approx(1 / 3))
    assert nucleus_only.nuclear_overlap_share == 1.0


def test_a_cell_with_zero_retention_stays_in_the_denominator(podocytes_with_lrp2_or_cubn):
    result = audit_population([podocytes_with_lrp2_or_cubn], "Podocyte", ["LRP2", "CUBN"], [DEFAULT, NUCLEUS_ONLY])

    values = by_condition(result.sections[0])
    assert result.sections[0].cells_labelled == 5
    # p5 keeps nothing and p4 never had a molecule; both still count in the five-cell denominator.
    assert values[NUCLEUS_ONLY].cells_with_retained_molecule == 3
    assert values[NUCLEUS_ONLY].cells_expressing == 1
    assert values[NUCLEUS_ONLY].observed_value == pytest.approx(1 / 5)


def test_seeded_monte_carlo_thinning_agrees_with_the_closed_form(podocytes_with_lrp2_or_cubn):
    """Thin the fixture's molecules at random, many times, and compare the mean share of podocytes keeping LRP2 or
    CUBN with the closed-form expectations. Retention probabilities come from the fixture's construction."""
    result = audit_population([podocytes_with_lrp2_or_cubn], "Podocyte", ["LRP2", "CUBN"], [DEFAULT, NUCLEUS_ONLY])
    closed = by_condition(result.sections[0])[NUCLEUS_ONLY]

    rng = np.random.default_rng(20261102)
    draws = 200_000
    cells = 5

    def share(kept_p1_lrp2, kept_p2_cubn):
        return (kept_p1_lrp2.astype(int) + kept_p2_cubn.astype(int)) / cells

    # Home-matched: every LRP2 molecule survives with 0.75, every CUBN molecule with 0.5.
    home = share((rng.random((draws, 2)) < 0.75).any(axis=1), rng.random(draws) < 0.5)
    # Cell-matched: p1's molecules survive with 0.8, p2's with 0.5.
    cellwise = share((rng.random((draws, 2)) < 0.8).any(axis=1), rng.random(draws) < 0.5)

    for simulated, expected in ((home, closed.expectation_home_matched), (cellwise, closed.expectation_cell_matched)):
        standard_error = simulated.std() / np.sqrt(draws)
        assert abs(simulated.mean() - expected) < 4 * standard_error


@pytest.fixture
def one_pair(tmp_path):
    """A marker-pair artifact with the single frozen pair CD3D / UMOD."""
    path = tmp_path / "pairs.json"
    path.write_text(json.dumps({"frozen_on": "test", "source": {"dataset": "hand-built"}, "pairs": [{"genes": ["CD3D", "UMOD"]}]}))
    return load_marker_pairs(path)


@pytest.fixture
def t_cells_with_umod():
    """Four T cells and one TAL cell (UMOD's home type).

    - t1: CD3D nuclear, UMOD outside the nucleus. t2: CD3D nuclear. t3: CD3D and UMOD nuclear. t4: nothing.
    - tal1: UMOD x2, one nuclear, so UMOD's home-matched retention is 0.5; CD3D's (in T cells) is 1.

    Co-expression (both / either): default 2/3 (t1, t3 of t1-t3); nucleus-only 1/3 (t3).
    Home-matched: p_CD3D = 1 for t1-t3, p_UMOD = 0.5 for t1 and t3 -> sum(p p) = 1, sum(p + p - p p) = 3 -> 1/3.
    Cell-matched: retention t1 1/2, t2 1, t3 1 -> sum(p p) = 0.25 + 1 = 1.25, sum(p + p - p p) = 0.75 + 1 + 1 -> 5/11.
    The result's molecules are the foreign marker UMOD in T cells: 2 by default, 1 kept (retention 1/2).
    """
    cells = [cell(f"t{i}", "T cell") for i in range(1, 5)] + [cell("tal1", "TAL")]
    molecules = [
        mol("m1", "CD3D", "t1", True), mol("m2", "UMOD", "t1", False),
        mol("m3", "CD3D", "t2", True),
        mol("m4", "CD3D", "t3", True), mol("m5", "UMOD", "t3", True),
        mol("m6", "UMOD", "tal1", True), mol("m7", "UMOD", "tal1", False),
    ]
    return section("HAND-COEX", cells, molecules)


def test_co_expression_score_and_its_expectations_match_hand_calculations(t_cells_with_umod, one_pair):
    result = audit_population(
        [t_cells_with_umod], "T cell", conditions=[DEFAULT, NUCLEUS_ONLY], measure="co_expression_score", marker_pairs=one_pair
    )

    values = by_condition(result.sections[0])
    assert result.gene_pairs == [["CD3D", "UMOD"]]
    assert values[DEFAULT].observed_value == pytest.approx(2 / 3)
    assert values[NUCLEUS_ONLY].observed_value == pytest.approx(1 / 3)
    assert values[NUCLEUS_ONLY].expectation_home_matched == pytest.approx(1 / 3)
    assert values[NUCLEUS_ONLY].expectation_cell_matched == pytest.approx(5 / 11)
    assert (values[NUCLEUS_ONLY].molecules, values[NUCLEUS_ONLY].retention) == (1, pytest.approx(0.5))


def test_every_audit_result_records_the_frozen_marker_pair_artifact_and_its_checksum(podocytes_with_lrp2_or_cubn):
    frozen = REPO / "configs" / "exclusive_marker_pairs.json"

    for result in (
        audit_population([podocytes_with_lrp2_or_cubn], "Podocyte", ["LRP2"], [DEFAULT, NUCLEUS_ONLY]),
        audit_population([podocytes_with_lrp2_or_cubn], "Podocyte", conditions=[DEFAULT, NUCLEUS_ONLY], measure="co_expression_score"),
    ):
        assert result.marker_pairs is not None
        assert result.marker_pairs.sha256 == hashlib.sha256(frozen.read_bytes()).hexdigest()
        assert result.marker_pairs.path == "configs/exclusive_marker_pairs.json"
        assert result.marker_pairs.source_dataset == "GSE271188"
        assert result.marker_pairs.pair_count == 40


def test_neighbour_proximity_share_for_excluded_and_retained_molecules():
    """A B cell at (0, 0) and a TAL cell (UMOD's home type) at (10, 0). The B cell's UMOD molecules:
    m1 at (1, 0), nuclear: 1 from its own centroid, 9 from the TAL cell -> retained, not closer to TAL.
    m2 at (7, 0), outside the nucleus: 7 from its own, 3 from TAL -> excluded, closer to TAL.
    m3 at (-4, 0), outside the nucleus: 4 from its own, 14 from TAL -> excluded, not closer.
    Under nucleus-only: excluded share 1/2, retained share 0/1."""
    tissue = section(
        "HAND-NEIGHBOUR",
        [cell("b1", "B cell", 0, 0), cell("tal1", "TAL", 10, 0)],
        [
            mol("m1", "UMOD", "b1", True, 1, 0),
            mol("m2", "UMOD", "b1", False, 7, 0),
            mol("m3", "UMOD", "b1", False, -4, 0),
            mol("m4", "UMOD", "tal1", True, 10, 0),
        ],
    )

    result = audit_population([tissue], "B cell", ["UMOD"], [DEFAULT, NUCLEUS_ONLY])

    nucleus_only = by_condition(result.sections[0])[NUCLEUS_ONLY]
    assert nucleus_only.neighbour_proximity_share_excluded == pytest.approx(0.5)
    assert nucleus_only.neighbour_proximity_share_retained == 0.0
    default = by_condition(result.sections[0])[DEFAULT]
    assert default.neighbour_proximity_share_excluded is None
    assert "neighbour_proximity_share_excluded" in default.missing_reasons


def test_evidence_regions_rank_150_um_windows_by_excluded_molecules_of_the_finding():
    """Windows are 150 µm squares anchored at (0, 0). B-cell UMOD molecules excluded under nucleus-only:
    three in window (0, 0), one in window (150, 0), two in window (0, 150). A TAL cell's excluded UMOD molecules
    (outside the population) and a nuclear B-cell molecule in window (300, 0) never count."""
    cells = [cell("b1", "B cell", 50, 50), cell("b2", "B cell", 200, 50), cell("b3", "B cell", 50, 200), cell("b4", "B cell", 320, 20), cell("tal1", "TAL", 400, 400)]
    molecules = [
        mol("a1", "UMOD", "b1", False, 10, 10), mol("a2", "UMOD", "b1", False, 20, 20), mol("a3", "UMOD", "b1", False, 30, 30),
        mol("b1m", "UMOD", "b2", False, 160, 10),
        mol("c1", "UMOD", "b3", False, 10, 160), mol("c2", "UMOD", "b3", False, 20, 170),
        mol("d1", "UMOD", "b4", True, 320, 20),
        *(mol(f"x{i}", "UMOD", "tal1", False, 400, 400) for i in range(5)),
    ]
    result = audit_population([section("HAND-REGIONS", cells, molecules)], "B cell", ["UMOD"], [DEFAULT, NUCLEUS_ONLY])

    ranked = [(r.rank, r.region.x0, r.region.y0, r.region.x1 - r.region.x0, r.excluded_molecules) for r in result.evidence_regions]
    assert ranked == [(1, 0, 0, 150, 3), (2, 0, 150, 150, 2), (3, 150, 0, 150, 1)]
    assert all(r.condition == NUCLEUS_ONLY for r in result.evidence_regions)
    assert "150" in result.ranking_rule and "excluded" in result.ranking_rule


def lrp2_section(section_id, podocytes, expressing, nuclear_in_podocytes):
    """`podocytes` podocytes; the first `expressing` carry one LRP2 molecule each (all nuclear, or all outside the
    nucleus), plus 10 more LRP2 molecules on the first podocyte so the molecule gate passes. A PT cell holds 4
    nuclear LRP2 molecules, so LRP2's home-matched retention under nucleus-only is 1."""
    cells = [cell(f"{section_id}-p{i}", "Podocyte") for i in range(podocytes)] + [cell(f"{section_id}-pt", "PT")]
    molecules = [mol(f"{section_id}-m{i}", "LRP2", f"{section_id}-p{i}", nuclear_in_podocytes) for i in range(expressing)]
    molecules += [mol(f"{section_id}-g{i}", "LRP2", f"{section_id}-p0", nuclear_in_podocytes) for i in range(10)]
    molecules += [mol(f"{section_id}-h{i}", "LRP2", f"{section_id}-pt", True) for i in range(4)]
    return section(section_id, cells, molecules)


def test_an_audit_is_segmentation_sensitive_when_observed_falls_below_the_home_expectation_in_every_leave_one_out():
    """Podocyte LRP2 is entirely outside the nucleus while PT LRP2 is entirely nuclear: nucleus-only keeps none of
    it, against a home-matched expectation equal to the default share."""
    sections = [lrp2_section(f"S{i}", 20, 10, nuclear_in_podocytes=False) for i in range(1, 4)]

    result = audit_population(sections, "Podocyte", ["LRP2"], [DEFAULT, NUCLEUS_ONLY])

    assert result.label == EvidenceStatus.SEGMENTATION_SENSITIVE
    assert [v.verdict for v in result.leave_one_section_out] == [EvidenceStatus.SEGMENTATION_SENSITIVE] * 3


def test_an_audit_is_stable_when_observed_matches_the_home_expectation():
    sections = [lrp2_section(f"S{i}", 20, 10, nuclear_in_podocytes=True) for i in range(1, 4)]

    result = audit_population(sections, "Podocyte", ["LRP2"], [DEFAULT, NUCLEUS_ONLY])

    assert result.label == EvidenceStatus.STABLE
    pooled = {p.condition: p for p in result.pooled}
    assert pooled[NUCLEUS_ONLY].observed_value == pytest.approx(30 / 60)
    assert pooled[NUCLEUS_ONLY].expectation_home_matched == pytest.approx(30 / 60)


def test_an_audit_whose_verdict_flips_when_one_section_is_left_out_is_insufficient_evidence():
    """S1 and S2 are stable (20 podocytes, 10 nuclear expressers each); S3 has 100 podocytes, all expressing outside
    the nucleus. Pooled: observed 20/140 against an expectation of 120/140, sensitive; without S3, stable."""
    sections = [
        lrp2_section("S1", 20, 10, nuclear_in_podocytes=True),
        lrp2_section("S2", 20, 10, nuclear_in_podocytes=True),
        lrp2_section("S3", 100, 100, nuclear_in_podocytes=False),
    ]

    result = audit_population(sections, "Podocyte", ["LRP2"], [DEFAULT, NUCLEUS_ONLY])

    pooled = {p.condition: p for p in result.pooled}
    assert pooled[NUCLEUS_ONLY].observed_value == pytest.approx(20 / 140)
    assert pooled[NUCLEUS_ONLY].expectation_home_matched == pytest.approx(120 / 140)
    assert result.label == EvidenceStatus.INSUFFICIENT_EVIDENCE
    assert "S3" in result.label_reason


def test_a_gene_without_a_home_cell_type_is_insufficient_evidence():
    sections = []
    for i in range(1, 4):
        cells = [cell(f"S{i}-p{j}", "Podocyte") for j in range(20)]
        molecules = [mol(f"S{i}-m{j}", "C3", f"S{i}-p{j % 20}", True) for j in range(12)]
        sections.append(section(f"S{i}", cells, molecules))

    result = audit_population(sections, "Podocyte", ["C3"], [DEFAULT, NUCLEUS_ONLY])

    assert result.label == EvidenceStatus.INSUFFICIENT_EVIDENCE
    assert "home cell type" in result.label_reason


def test_a_duplicate_section_is_listed_as_left_out_and_never_counted(podocytes_with_lrp2_or_cubn):
    result = audit_population(
        [podocytes_with_lrp2_or_cubn],
        "Podocyte",
        ["LRP2"],
        [DEFAULT, NUCLEUS_ONLY],
        section_groups={"HAND-HERO": "Control"},
        sections_left_out={"HAND-DUP": "duplicate_of HAND-HERO"},
    )

    assert [(s.section_id, s.reason) for s in result.sections_left_out] == [("HAND-DUP", "duplicate_of HAND-HERO")]
    assert [s.section_id for s in result.sections] == ["HAND-HERO"]
    assert result.sections[0].group == "Control"


def test_the_label_sensitivity_check_reports_both_rules_with_cell_counts():
    """The same section under two label rules: c1 and c2 are podocytes under both; c3 only under the first rule,
    c4 only under the second."""
    def labelled(rule, podocytes):
        cells = [cell(c, "Podocyte" if c in podocytes else "PT") for c in ("c1", "c2", "c3", "c4")]
        return make_section("S1", "hand-built", rule, cells=cells, molecules=[mol("m1", "LRP2", "c3", True)])

    check = label_sensitivity_check(
        {"rule-a": [labelled("rule-a", {"c1", "c2", "c3"})], "rule-b": [labelled("rule-b", {"c1", "c2", "c4"})]},
        "Podocyte",
        ["LRP2", "CUBN"],
        [DEFAULT, NUCLEUS_ONLY],
    )

    assert [(arm.label_rule_id, arm.cells_labelled) for arm in check.arms] == [("rule-a", 3), ("rule-b", 3)]
    assert (check.cells_in_both, check.cells_only_first, check.cells_only_second) == (2, 1, 1)
    assert check.control_id.startswith("ctl-")


@pytest.fixture
def two_glomeruli():
    """Left half (x < 100): 25 podocytes, each with one LRP2 molecule outside the nucleus, and a PT cell with 4
    nuclear LRP2 molecules. Right half (x >= 100): 5 podocytes, each with one nuclear LRP2 molecule, and a PT cell
    with 4 LRP2 molecules outside the nucleus. One podocyte sits at x = 95 with its LRP2 molecule at x = 105."""
    cells, molecules = [], []
    for i in range(25):
        cells.append(cell(f"L{i}", "Podocyte", 10 + i, 10))
        molecules.append(mol(f"Lm{i}", "LRP2", f"L{i}", False, 10 + i, 11))
    cells.append(cell("Lpt", "PT", 50, 50))
    molecules += [mol(f"Lpt{i}", "LRP2", "Lpt", True, 50, 50) for i in range(4)]
    for i in range(5):
        cells.append(cell(f"R{i}", "Podocyte", 150 + i, 10))
        molecules.append(mol(f"Rm{i}", "LRP2", f"R{i}", True, 150 + i, 10))
    cells.append(cell("Rpt", "PT", 150, 50))
    molecules += [mol(f"Rpt{i}", "LRP2", "Rpt", False, 150, 50) for i in range(4)]
    cells.append(cell("edge", "Podocyte", 95, 10))
    molecules.append(mol("edge-m", "LRP2", "edge", True, 105, 10))
    return section("HAND-ROI", cells, molecules)


def test_an_roi_scopes_the_population_expectations_and_gates_to_the_box(two_glomeruli):
    """Inside the left box: 26 podocytes (25 plus the edge cell, whose centroid is inside; its molecule outside the
    box comes with it), 26 LRP2 molecules. Default share 26/26; nucleus-only keeps only the edge cell's: 1/26.
    The home-matched retention comes from the left PT cell alone (1), so the expectation is 26/26."""
    box = Region(section_id="HAND-ROI", x0=0, y0=0, x1=100, y1=100)

    result = audit_population([two_glomeruli], "Podocyte", ["LRP2"], [DEFAULT, NUCLEUS_ONLY], roi=box)

    values = by_condition(result.sections[0])
    assert result.roi == box
    assert result.sections[0].cells_labelled == 26
    assert values[DEFAULT].molecules == 26
    assert values[NUCLEUS_ONLY].observed_value == pytest.approx(1 / 26)
    assert values[NUCLEUS_ONLY].expectation_home_matched == pytest.approx(1.0)
    assert result.sections[0].eligible
    assert all(r.region.x1 <= 150 for r in result.evidence_regions)


def test_a_whole_section_result_has_no_roi(two_glomeruli):
    result = audit_population([two_glomeruli], "Podocyte", ["LRP2"], [DEFAULT, NUCLEUS_ONLY])

    assert result.roi is None
    assert result.sections[0].cells_labelled == 31


def test_a_box_that_fails_the_gates_is_reported_as_failing(two_glomeruli):
    """The right box holds 5 podocytes and 5 LRP2 molecules: below both gates."""
    box = Region(section_id="HAND-ROI", x0=100, y0=0, x1=200, y1=100)

    status = gate_status(two_glomeruli, box, "Podocyte", ["LRP2", "CUBN"])
    result = audit_population([two_glomeruli], "Podocyte", ["LRP2"], [DEFAULT, NUCLEUS_ONLY], roi=box)

    assert (status.cells, status.molecules) == (5, 5)
    assert (status.passes_population_gate, status.passes_molecule_gate) == (False, False)
    assert "below population gate" in status.status
    assert not result.sections[0].eligible
    assert result.label == EvidenceStatus.INSUFFICIENT_EVIDENCE


def test_gate_status_counts_the_population_and_its_molecules_in_the_box(two_glomeruli):
    box = Region(section_id="HAND-ROI", x0=0, y0=0, x1=100, y1=100)

    status = gate_status(two_glomeruli, box, "Podocyte", ["LRP2"])

    assert (status.cells, status.molecules, status.passes_population_gate, status.passes_molecule_gate) == (26, 26, True, True)
    assert gate_status(two_glomeruli, None, "Podocyte", ["LRP2"]).cells == 31
