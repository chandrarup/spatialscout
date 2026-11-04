"""Seam 1: claim verification on hand-built molecule tables with known answers.

Three sections, each built the same way (so pooled values equal per-section ones):

- 25 podocytes p0..p24 on a line, 20 µm apart. p0..p9 carry LRP2 x2 (one nuclear, one 4 µm out of the nucleus);
  p10..p19 carry one LRP2 4 µm out; p20..p24 none. Each podocyte also has NPHS1 x1 nuclear.
- 5 PT cells (LRP2's home type) 6 µm from p10..p14, each with LRP2 x4, all nuclear.

Share expressing LRP2: default 20/25 = 0.8; nucleus-only 10/25 = 0.4. PT retains all its LRP2 under nucleus-only,
so the home-matched expectation is 0.8, and 0.4 < 0.8 x 2^-0.5: the stated direction must be "drops".
Neighbour proximity under nucleus-only: of the 20 excluded molecules per section, the 5 of p10..p14 lie 2 µm from a
PT centroid but 4 µm from their own (share 0.25); no retained molecule is closer (share 0): excluded nearer home.
"""

import asyncio

import pytest

from spatialscout.contracts import (
    CheckResult,
    CitedNumber,
    Claim,
    ClaimControls,
    CompositeFigure,
    ConditionName,
    FindingRef,
    InjectedErrorKind,
    VerificationStatus,
)
from spatialscout.data import make_section
from spatialscout.engine import audit_population, label_sensitivity_check, random_thinning_control
from spatialscout.verify.inject import inject
from spatialscout.verify.recompute import recompute_audit
from spatialscout.verify.verifier import VerificationContext, combine, correct_claim, verify_claim

CONDITIONS = [ConditionName.DEFAULT, ConditionName.NUCLEUS_ONLY]
RULE, ALT_RULE = "hand-built", "hand-alternative"
SECTIONS = ("HAND-1", "HAND-2", "HAND-3")


def build_section(section_id, rule):
    cells, molecules = [], []

    def mol(gene, cell_id, x, y, nuclear):
        molecules.append({"molecule_id": f"m{len(molecules)}", "gene": gene, "cell_id": cell_id, "x": x, "y": y,
                          "overlaps_nucleus": nuclear, "nucleus_distance": 0.0 if nuclear else 4.0, "qv": 40.0})

    for i in range(25):
        x = i * 20.0
        # Under the alternative rule p24 is unlabelled, so the two rules disagree on one cell.
        cell_type = "Unlabelled" if (rule == ALT_RULE and i == 24) else "Podocyte"
        cells.append({"cell_id": f"p{i}", "cell_type": cell_type, "x": x, "y": 0.0, "nucleus_area": 28.3, "cell_area": 201.1})
        mol("NPHS1", f"p{i}", x, 0.5, True)
        if i < 10:
            mol("LRP2", f"p{i}", x, 0.5, True)
        if i < 20:
            mol("LRP2", f"p{i}", x, 4.0, False)
    for i in range(10, 15):
        x = i * 20.0
        cells.append({"cell_id": f"pt{i}", "cell_type": "PT", "x": x, "y": 6.0, "nucleus_area": 28.3, "cell_area": 201.1})
        for _ in range(4):
            mol("LRP2", f"pt{i}", x, 6.0, True)
    return make_section(section_id, "hand-built", rule, molecules=molecules, cells=cells)


BY_RULE = {rule: [build_section(s, rule) for s in SECTIONS] for rule in (RULE, ALT_RULE)}


def load_sections(section_ids, rule):
    return [s for s in BY_RULE[rule] if s.section_id in section_ids]


@pytest.fixture(scope="module")
def world():
    finding = audit_population(BY_RULE[RULE], "Podocyte", ["LRP2"], CONDITIONS)
    thinning = random_thinning_control(finding)
    labels = label_sensitivity_check({RULE: BY_RULE[RULE], ALT_RULE: BY_RULE[ALT_RULE]}, "Podocyte", ["LRP2"], CONDITIONS)
    figure = CompositeFigure(figure_id="fig-hand", finding_id=finding.finding_id, path="figures/hand.png", sha256="0",
                             crop=None, panel_a="A", panel_b="B")
    other = CompositeFigure(figure_id="fig-other", finding_id="fnd-other", path="figures/other.png", sha256="1",
                            crop=None, panel_a="A", panel_b="B")
    claim = Claim(
        claim_id="clm-hand",
        investigation_id="inv-hand",
        dataset_id="hand-built",
        finding=FindingRef(finding_id=finding.finding_id, finding_kind="audit"),
        text="In cells labelled Podocyte by our hand-built rule, the share expressing LRP2 drops from 80% to 40% under "
        "nucleus-only, below the home-matched expectation of 80% x 2^-0.5, over 3 eligible sections; excluded molecules lie "
        "closer to a cell of their gene's home type more often than retained molecules do.",
        cited={
            "eligible": CitedNumber(value=3, source="eligible_section_ids.count"),
            "default": CitedNumber(value=0.8, source="pooled[default].observed_value"),
            "nucleus_only": CitedNumber(value=0.4, source="pooled[nucleus_only].observed_value"),
            "home": CitedNumber(value=0.8, source="pooled[nucleus_only].expectation_home_matched"),
            "near_excluded": CitedNumber(value=0.25, source="sections[HAND-1].conditions[nucleus_only].neighbour_proximity_share_excluded"),
            "alt_cells": CitedNumber(value=72, source=f"controls[{labels.control_id}].arms[{ALT_RULE}].cells_labelled"),
        },
        controls=ClaimControls(random_thinning=thinning.control_id, label_sensitivity=labels.control_id),
        evidence_status=finding.label,
        direction="drops",
        neighbour_pattern="excluded_nearer_home",
    )
    context = VerificationContext(
        datasets=["hand-built", "GSE286184"],
        findings={finding.finding_id: finding},
        controls={thinning.control_id: thinning, labels.control_id: labels},
        figures={"fig-hand": figure, "fig-other": other},
        load_sections=load_sections,
    )
    return finding, claim, context


def verify(claim, context):
    return asyncio.run(verify_claim(claim, context))


def checks(verification):
    return {c.kind: c for c in verification.checks}


def test_the_independent_recompute_matches_the_engine_on_hand_built_tables(world):
    finding, _, _ = world
    recomputed = recompute_audit(BY_RULE[RULE], "Podocyte", ["LRP2"], "share_expressing", ["default", "nucleus_only"])

    pooled = {p["condition"]: p for p in recomputed.pooled}
    assert pooled["default"]["observed_value"] == pytest.approx(0.8)
    assert pooled["nucleus_only"]["observed_value"] == pytest.approx(0.4)
    assert pooled["nucleus_only"]["expectation_home_matched"] == pytest.approx(0.8)
    assert recomputed.direction == "drops"
    assert recomputed.eligible_section_ids == list(finding.eligible_section_ids) == list(SECTIONS)
    for engine, independent in zip(finding.pooled, recomputed.pooled, strict=True):
        for name in ("cells", "molecules", "default_molecules", "retention", "observed_value", "expectation_cell_matched",
                     "expectation_home_matched", "excess_drop_cell_matched", "excess_drop_home_matched"):
            assert independent[name] == pytest.approx(getattr(engine, name)), name
    for engine, independent in zip(finding.sections, recomputed.sections, strict=True):
        assert independent.cells_labelled == engine.cells_labelled == 25
        for e, i in zip(engine.conditions, independent.conditions, strict=True):
            for name in ("molecules", "retention", "observed_value", "expectation_cell_matched", "expectation_home_matched",
                         "neighbour_proximity_share_excluded", "neighbour_proximity_share_retained", "nuclear_overlap_share"):
                assert i[name] == pytest.approx(getattr(e, name)), (engine.section_id, e.condition, name)
    hand1 = {c.condition: c for c in recomputed.sections[0].conditions}
    assert hand1["nucleus_only"].neighbour_proximity_share_excluded == pytest.approx(0.25)
    assert hand1["nucleus_only"].neighbour_proximity_share_retained == pytest.approx(0.0)


def test_a_correct_claim_passes_the_structural_and_numerical_checks(world):
    _, claim, context = world
    verified, verification = verify(claim, context)

    assert checks(verification)["structural"].status == "passed", checks(verification)["structural"].reasons
    assert checks(verification)["numerical"].status == "passed", checks(verification)["numerical"].reasons
    # No gateway here, so the visual check cannot run and the claim is unavailable, never verified.
    assert checks(verification)["visual"].status == "unavailable"
    assert verified.verification_status == VerificationStatus.UNAVAILABLE
    assert verification.in_validated_summary


DETERMINISTIC_KINDS = {
    InjectedErrorKind.REVERSED_DIRECTION: "numerical",
    InjectedErrorKind.WRONG_SECTION_COUNT: "structural",
    InjectedErrorKind.WRONG_DATASET_REFERENCE: "structural",
    InjectedErrorKind.CHANGED_EFFECT: "numerical",
    InjectedErrorKind.FIGURE_LABEL_MISMATCH: "structural",
    InjectedErrorKind.MISSTATED_SPATIAL_PATTERN: "numerical",
    InjectedErrorKind.MISSING_REQUIRED_CONTROL: "structural",
}


@pytest.mark.parametrize("kind", list(DETERMINISTIC_KINDS), ids=lambda k: k.value)
def test_every_deterministic_error_kind_is_caught(world, kind):
    finding, claim, context = world
    variant, changes = inject(kind, claim, finding, other_figure_id="fig-other")

    _, verification = verify(variant, context)

    assert variant.injected.is_injected and variant.injected.kind == kind
    assert changes, "an injected error must change the claim"
    assert verification.verification_status == VerificationStatus.FAILED
    assert checks(verification)[DETERMINISTIC_KINDS[kind]].status == "failed"
    assert not verification.in_validated_summary


def test_a_claim_missing_its_label_sensitivity_check_fails_structurally(world):
    _, claim, context = world
    skipped = claim.model_copy(update={"controls": ClaimControls(random_thinning=claim.controls.random_thinning)})

    verified, verification = verify(skipped, context)

    structural = checks(verification)["structural"]
    assert structural.status == "failed"
    assert any("required control not run" in r and "label-sensitivity" in r for r in structural.reasons)
    assert verified.verification_status == VerificationStatus.FAILED


def test_a_label_rule_that_competes_with_the_genes_home_type_requires_the_label_sensitivity_check(world):
    """The NPHS1-anchored rule ignores LRP2 but decides podocyte membership against PT, LRP2's home type."""
    from spatialscout.contracts import LabelRule
    from spatialscout.verify.checks import required_controls

    finding, _, _ = world
    anchored = LabelRule(label_rule_id=RULE, description="anchored", markers={"Podocyte": ["NPHS1"], "PT": []},
                         ignored_genes=["LRP2", "CUBN"], score_threshold=0.5, min_molecules=5)
    unrelated = LabelRule(label_rule_id=RULE, description="unrelated", markers={"Podocyte": ["NPHS1"]},
                          ignored_genes=[], score_threshold=0.5, min_molecules=5)

    assert "label_sensitivity" in required_controls(finding, [anchored])
    assert "label_sensitivity" not in required_controls(finding, [unrelated])


def _check(kind, status):
    return CheckResult(kind=kind, status=status, details="")


def test_claim_states_follow_the_rules():
    assert combine([_check("structural", "failed"), _check("numerical", "passed"), _check("visual", "passed")]) == VerificationStatus.FAILED
    assert combine([_check("structural", "passed"), _check("numerical", "failed"), _check("visual", "disputed")]) == VerificationStatus.FAILED
    assert combine([_check("structural", "passed"), _check("numerical", "passed"), _check("visual", "disputed")]) == VerificationStatus.DISPUTED
    assert combine([_check("structural", "passed"), _check("numerical", "passed"), _check("visual", "passed")]) == VerificationStatus.VERIFIED


def test_a_correction_is_a_new_claim_version(world):
    _, claim, _ = world
    corrected = correct_claim(claim.model_copy(update={"verification_status": VerificationStatus.FAILED}), text="Corrected.")

    assert corrected.claim_id == claim.claim_id
    assert corrected.version == claim.version + 1
    assert corrected.verification_status == VerificationStatus.PENDING
    assert claim.text != "Corrected."
