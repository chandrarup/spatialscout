"""Verification and review contracts.

Verification (ticket 10): three checks on every claim version, each with its reasons.

- structural: schema, the dataset, finding, figure and control references, section counts, required controls;
- numerical: an independent code path recomputes every cited number, the stated direction and the stated
  neighbour pattern from the stored molecule tables, within the declared tolerances;
- visual: Muse Spark 1.3 reads the composite figure and answers three questions (`VisualAnswer`).

The verification status they add up to: a structural or numerical failure fails the claim (blocked from the
validated summary, kept in history); a visual disagreement disputes it; a check that could not run leaves it
unavailable; otherwise it is verified. Injected variants (`ClaimChallenge`) are verified the same way.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from .base import SCHEMA_VERSION, Contract
from .claim import Claim, InjectedErrorKind, VerificationStatus
from .finding import CompositeFigure

CheckKind = Literal["structural", "numerical", "visual"]


class CheckResult(Contract):
    kind: CheckKind
    status: Literal["passed", "failed", "disputed", "unavailable"]
    details: str
    reasons: list[str] = Field(default_factory=list, description="Every problem the check found; empty when it passed.")


class VisualAnswer(Contract):
    """Muse Spark 1.3's reading of a composite figure, against this schema. A consistency check, not ground truth."""

    panel_a_direction: Literal["holds", "drops", "unclear"] = Field(
        description="What Panel A shows: holds when the pooled observed line stays at or above the threshold line under "
        "every stricter condition, drops when it falls below it under at least one."
    )
    panel_a_matches_claim: bool = Field(description="Panel A's direction is the direction the claim states.")
    single_section_drives_panel_a: bool = Field(description="One section's line alone accounts for Panel A's pooled direction.")
    panel_b_matches_claim: bool | None = Field(
        description="Panel B, read with the computed neighbour-proximity shares, shows the neighbour pattern the claim "
        "states; null when the claim states none."
    )
    explanation: str = Field(description="One or two sentences on what the panels show.")


class VerificationResult(Contract):
    """Every check run on one claim version, and the verification status they add up to."""

    schema_version: str = SCHEMA_VERSION
    claim_id: str
    claim_version: int
    checks: list[CheckResult]
    verification_status: VerificationStatus
    finding_id: str | None = None
    figure: CompositeFigure | None = Field(default=None, description="The composite figure the visual check read.")
    visual: VisualAnswer | None = None
    tolerances: dict[str, float] = Field(default_factory=dict, description="The declared tolerances of the numerical check.")
    recomputed: dict[str, Any] = Field(default_factory=dict, description="Each cited source's independently recomputed value.")
    in_validated_summary: bool = Field(default=False, description="False for a failed claim: it stays in history only.")


class FieldChange(Contract):
    """One field an injected error changed."""

    field: str
    before: Any
    after: Any


class ClaimChallenge(Contract):
    """One recorded injected variant of a claim and its recorded verification. `detected` is the recorded outcome:
    true when a check found a problem the original claim did not have (`new_reasons`), false for a miss."""

    kind: InjectedErrorKind
    claim: Claim
    verification: VerificationResult
    changes: list[FieldChange]
    new_reasons: list[str]
    detected: bool


class ClaimChallenges(Contract):
    """The "Challenge the verifier" options of one claim: its injected variants, named only by error kind."""

    schema_version: str = SCHEMA_VERSION
    claim_id: str
    claim_version: int
    base_status: VerificationStatus
    variants: list[ClaimChallenge]


class ReviewDecision(Contract):
    """The researcher's decision on one claim version; voice decisions need confirmation."""

    schema_version: str = SCHEMA_VERSION
    decision_id: str
    claim_id: str
    claim_version: int
    decision: Literal["accepted_for_follow_up", "needs_investigation", "unresolved"]
    reviewer: str
    decided_at_utc: datetime
    via: Literal["click", "voice"]
    confirmed: bool
