"""The hypothesis verdict rule (revision 3, ticket 10b): each sub-claim's verdict from the verified claims about its
population and genes. Deterministic and frozen; the models never write a verdict."""

from collections.abc import Mapping, Sequence

from ..contracts import Claim, EvidenceStatus, HypothesisVerdict, SubClaim, SubClaimVerdict, VerificationStatus

RULE = (
    "A sub-claim rests on the non-injected claims about its cell type and any of its genes. Each verified claim's "
    "outcome is 'holds' when its evidence label is stable and 'drops' when it is segmentation-sensitive. Confirmed: "
    "every claim is verified with an outcome, and every outcome is the predicted one. Refuted: every claim is verified "
    "with an outcome, and every outcome is the opposite. Inconclusive: no claim, a claim that is not verified (failed, "
    "disputed, unavailable or pending), insufficient evidence, or outcomes that disagree."
)
SCOPE = "In these sections and regions, under the controls each claim cites. A verdict says what this evidence supports, not whether the biology is true."
OUTCOME = {EvidenceStatus.STABLE: "holds", EvidenceStatus.SEGMENTATION_SENSITIVE: "drops"}
LABEL_TEXT = {EvidenceStatus.STABLE: "stable", EvidenceStatus.SEGMENTATION_SENSITIVE: "segmentation-sensitive"}


def _matches(sub: SubClaim, population: tuple[str, Sequence[str]]) -> bool:
    cell_type, genes = population
    return cell_type.lower() == sub.cell_type.lower() and bool({g.upper() for g in genes} & {g.upper() for g in sub.genes})


def derive_verdicts(
    sub_claims: Sequence[SubClaim],
    claims: Sequence[Claim],
    populations: Mapping[str, tuple[str, Sequence[str]]],
    *,
    dataset_id: str,
) -> list[SubClaimVerdict]:
    """`populations` maps each finding id to its (cell type, genes)."""
    verdicts = []
    for sub in sub_claims:
        mine = [c for c in claims if not c.injected.is_injected and c.finding.finding_id in populations
                and _matches(sub, populations[c.finding.finding_id])]
        ids = [c.claim_id for c in mine]
        problems = [f"claim {c.claim_id}: verification {c.verification_status.value}" for c in mine if c.verification_status != VerificationStatus.VERIFIED]
        problems += [f"claim {c.claim_id} has insufficient evidence" for c in mine
                     if c.verification_status == VerificationStatus.VERIFIED and c.evidence_status not in OUTCOME]
        if not mine:
            verdict, reason = "inconclusive", f"no claim tested {sub.cell_type} {'/'.join(sub.genes)}"
        elif problems:
            verdict, reason = "inconclusive", "; ".join(problems)
        else:
            outcomes = {OUTCOME[c.evidence_status] for c in mine}
            labels = ", ".join(f"{c.claim_id} {LABEL_TEXT[c.evidence_status]}" for c in mine)
            if outcomes == {sub.predicted}:
                verdict, reason = "confirmed", f"predicted '{sub.predicted}'; verified: {labels}"
            elif sub.predicted not in outcomes:
                verdict, reason = "refuted", f"predicted '{sub.predicted}'; verified: {labels}"
            else:
                verdict, reason = "inconclusive", f"verified claims disagree: {labels}"
        verdicts.append(SubClaimVerdict(sub_claim=sub, verdict=verdict, reason=reason, claim_ids=ids, dataset_id=dataset_id))
    return verdicts


def hypothesis_verdict(question: str, verdicts: list[SubClaimVerdict]) -> HypothesisVerdict:
    return HypothesisVerdict(question=question, scope=SCOPE, verdicts=verdicts, rule=RULE)
