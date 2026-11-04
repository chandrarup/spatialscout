"""Verify a claim: the structural, numerical and visual checks, and the verification status they add up to.

| Check result | Claim |
| --- | --- |
| Numerical or structural failure | failed: blocked from the validated summary, kept in history |
| Visual disagreement | disputed: stays visible, flagged for review |
| A check that could not run | unavailable |
| Every check passed | verified |

A correction never edits a claim: it is a new version (`correct_claim`), verified afresh.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from ..contracts import (
    AuditResult,
    CheckResult,
    Claim,
    ClaimChallenge,
    ClaimChallenges,
    CompositeFigure,
    InjectedError,
    InjectedErrorKind,
    LabelRuleSet,
    LabelSensitivityCheck,
    VerificationResult,
    VerificationStatus,
)
from ..data import SectionTables
from ..gateway import ModelGateway
from .checks import numerical_check, structural_check
from .inject import inject
from .recompute import TOLERANCES, Node, recompute_audit
from .visual import visual_check

SectionsLoader = Callable[[Sequence[str], str], Sequence[SectionTables]]
"""Load the named sections under a label rule."""


@dataclass
class VerificationContext:
    """What verification can see: the investigation's findings, controls and figures, the datasets served, the frozen
    label rules, the molecule tables (through `load_sections`) and the gateway for the visual check."""

    datasets: Sequence[str]
    findings: Mapping[str, AuditResult]
    controls: Mapping[str, BaseModel]
    figures: Mapping[str, CompositeFigure] = field(default_factory=dict)
    figure_png: Mapping[str, bytes] = field(default_factory=dict)
    label_rules: LabelRuleSet | None = None
    load_sections: SectionsLoader | None = None
    gateway: ModelGateway | None = None
    _recomputed: dict[str, Node | str] = field(default_factory=dict)
    _visual_memo: dict[str, Any] = field(default_factory=dict)

    def figure_for(self, finding_id: str) -> CompositeFigure | None:
        return next((f for f in self.figures.values() if f.finding_id == finding_id), None)

    def recompute(self, finding: AuditResult, label_rule_id: str | None = None) -> Node | str:
        """The independent recompute of a finding (under another label rule for a label-check arm), or why not."""
        rule = label_rule_id or finding.population.label_rule_id
        key = f"{finding.finding_id}:{rule}"
        if key not in self._recomputed:
            if self.load_sections is None:
                self._recomputed[key] = "no molecule tables are available to recompute from"
            else:
                try:
                    sections = self.load_sections([s.section_id for s in finding.sections], rule)
                    self._recomputed[key] = recompute_audit(
                        sections, finding.population.cell_type, finding.genes, finding.measure,
                        [p.condition.value for p in finding.pooled] or [c.condition.value for c in finding.sections[0].conditions],
                        finding.gene_pairs, finding.roi,
                    )
                except Exception as error:  # noqa: BLE001 - a recompute that cannot run leaves the check unavailable
                    self._recomputed[key] = f"the molecule tables could not be read: {type(error).__name__}: {error}"
        return self._recomputed[key]


async def verify_claim(claim: Claim, context: VerificationContext) -> tuple[Claim, VerificationResult]:
    """Run the three checks on one claim version. Returns the claim with its verification status (and the figure the
    visual check read, when it cited none) and the full result."""
    finding = context.findings.get(claim.finding.finding_id)
    structural = structural_check(claim, finding, context.controls, context.figures, context.datasets, context.label_rules)

    recomputed: Node | None = None
    unavailable = None
    arms: dict[str, Node] = {}
    if finding is not None:
        result = context.recompute(finding)
        recomputed, unavailable = (result, None) if isinstance(result, Node) else (None, result)
        label_check = context.controls.get(claim.controls.label_sensitivity or "")
        if recomputed is not None and isinstance(label_check, LabelSensitivityCheck):
            for arm in label_check.arms:
                arm_result = context.recompute(finding, arm.label_rule_id)
                if isinstance(arm_result, Node):
                    arms[arm.label_rule_id] = arm_result
    numerical, values = numerical_check(claim, finding, context.controls, recomputed, arms, unavailable)

    figure = context.figures.get(claim.figure_id) if claim.figure_id else (context.figure_for(finding.finding_id) if finding else None)
    png = context.figure_png.get(figure.figure_id) if figure else None
    visual, answer = await visual_check(context.gateway, claim, finding, figure, png, context._visual_memo)

    checks = [structural, numerical, visual]
    status = combine(checks)
    verification = VerificationResult(
        claim_id=claim.claim_id,
        claim_version=claim.version,
        checks=checks,
        verification_status=status,
        finding_id=claim.finding.finding_id,
        figure=figure,
        visual=answer,
        tolerances=dict(TOLERANCES),
        recomputed={k: v for k, v in values.items() if v is None or isinstance(v, int | float | str)},
        in_validated_summary=status in (VerificationStatus.VERIFIED, VerificationStatus.DISPUTED, VerificationStatus.UNAVAILABLE),
    )
    update: dict[str, Any] = {"verification_status": status}
    if claim.figure_id is None and figure is not None:
        update["figure_id"] = figure.figure_id
    return claim.model_copy(update=update), verification


def combine(checks: Sequence[CheckResult]) -> VerificationStatus:
    statuses = {c.kind: c.status for c in checks}
    if statuses.get("structural") == "failed" or statuses.get("numerical") == "failed":
        return VerificationStatus.FAILED
    if statuses.get("visual") == "disputed":
        return VerificationStatus.DISPUTED
    if "unavailable" in statuses.values():
        return VerificationStatus.UNAVAILABLE
    return VerificationStatus.VERIFIED


def reasons_of(verification: VerificationResult) -> list[str]:
    return [reason for check in verification.checks if check.status in ("failed", "disputed") for reason in check.reasons]


def correct_claim(claim: Claim, **changes: Any) -> Claim:
    """A correction: a new version of the claim (same id, version + 1) with the changes, pending verification again.
    The earlier version is kept as it was."""
    return claim.model_copy(
        update={**changes, "version": claim.version + 1, "verification_status": VerificationStatus.PENDING, "injected": InjectedError()}
    )


async def challenge(
    base: Claim, base_verification: VerificationResult, context: VerificationContext, *, other_figure_id: str | None,
    kinds: Sequence[InjectedErrorKind] = tuple(InjectedErrorKind),
) -> ClaimChallenges:
    """Every injected variant of a claim, verified like any claim. A variant is detected when a check finds a problem
    the original claim did not have; otherwise it is recorded as a miss."""
    finding = context.findings[base.finding.finding_id]
    before = set(reasons_of(base_verification))
    variants = []
    for kind in kinds:
        variant, changes = inject(kind, base, finding, other_figure_id=other_figure_id)
        variant, verification = await verify_claim(variant, context)
        new = [r for r in reasons_of(verification) if r not in before]
        detected = bool(new) and verification.verification_status in (VerificationStatus.FAILED, VerificationStatus.DISPUTED)
        variants.append(ClaimChallenge(kind=kind, claim=variant, verification=verification, changes=changes, new_reasons=new, detected=detected))
    return ClaimChallenges(claim_id=base.claim_id, claim_version=base.version, base_status=base_verification.verification_status, variants=variants)
