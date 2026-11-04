"""Seam 1: the hypothesis verdict rule (ticket 10b) on hand-built claims: one test per row of the rule, including
a disputed claim that would otherwise confirm."""

from spatialscout.contracts import Claim, FindingRef, InjectedError, SubClaim
from spatialscout.verify.verdict import derive_verdicts

LRP2 = SubClaim(text="podocyte LRP2 presence persists", cell_type="Podocyte", genes=["LRP2", "CUBN"], predicted="holds")
UMOD = SubClaim(text="UMOD in B cells is admixture", cell_type="B cell", genes=["UMOD"], predicted="drops")
POPULATIONS = {"fnd-lrp2": ("Podocyte", ["LRP2", "CUBN"]), "fnd-umod": ("B cell", ["UMOD"]), "fnd-nphs1": ("Podocyte", ["NPHS1"])}


def claim(claim_id: str, finding_id: str, label: str, status: str = "verified", injected: bool = False) -> Claim:
    return Claim(claim_id=claim_id, investigation_id="inv", dataset_id="GSE286184",
                 finding=FindingRef(finding_id=finding_id, finding_kind="audit"), text="t", cited={},
                 evidence_status=label, verification_status=status, injected=InjectedError(is_injected=injected))


def verdict_of(sub: SubClaim, claims: list[Claim]):
    [v] = derive_verdicts([sub], claims, POPULATIONS, dataset_id="GSE286184")
    return v


def test_a_verified_stable_claim_confirms_a_holds_prediction():
    v = verdict_of(LRP2, [claim("c1", "fnd-lrp2", "stable")])
    assert (v.verdict, v.claim_ids) == ("confirmed", ["c1"])


def test_a_verified_segmentation_sensitive_claim_confirms_a_drops_prediction_and_refutes_a_holds_one():
    assert verdict_of(UMOD, [claim("c2", "fnd-umod", "segmentation_sensitive")]).verdict == "confirmed"
    refuted = verdict_of(LRP2, [claim("c1", "fnd-lrp2", "segmentation_sensitive")])
    assert refuted.verdict == "refuted" and "segmentation-sensitive" in refuted.reason


def test_a_disputed_or_failed_claim_never_confirms():
    assert verdict_of(LRP2, [claim("c1", "fnd-lrp2", "stable", status="disputed")]).verdict == "inconclusive"
    assert verdict_of(LRP2, [claim("c1", "fnd-lrp2", "stable"), claim("c3", "fnd-lrp2", "stable", status="failed")]).verdict == "inconclusive"


def test_insufficient_evidence_mixed_outcomes_or_no_claim_are_inconclusive():
    assert verdict_of(LRP2, [claim("c1", "fnd-lrp2", "insufficient_evidence")]).verdict == "inconclusive"
    mixed = verdict_of(LRP2, [claim("c1", "fnd-lrp2", "stable"), claim("c4", "fnd-lrp2", "segmentation_sensitive")])
    assert mixed.verdict == "inconclusive"
    none = verdict_of(UMOD, [claim("c1", "fnd-lrp2", "stable")])
    assert none.verdict == "inconclusive" and none.claim_ids == [] and "no claim" in none.reason


def test_injected_claims_and_other_populations_are_ignored():
    claims = [claim("c1", "fnd-lrp2", "stable"), claim("x1", "fnd-lrp2", "segmentation_sensitive", injected=True),
              claim("c5", "fnd-nphs1", "segmentation_sensitive")]
    v = verdict_of(LRP2, claims)
    assert (v.verdict, v.claim_ids) == ("confirmed", ["c1"])
