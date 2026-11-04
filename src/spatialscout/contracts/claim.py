"""Claim contracts (spec "Claim shape", schema 2.0): a sentence about one finding, the numbers, controls
and figure it cites, and three separate statuses: evidence, verification and review.

Each cited number names its source field inside the cited finding, as a path such as
`sections[SYN-01].conditions[nucleus_only].retention` or `sections[SYN-01].cells_labelled`, so the
independent recompute (ticket 10) can check every number. Missing values stay null; a missing number never
becomes zero. `figure_id` and the control ids stay null until tickets 05, 06 and 09a produce them.
"""

from enum import StrEnum
from typing import Literal

from pydantic import Field

from .base import Contract, EvidenceStatus, FindingKind

CLAIM_SCHEMA_VERSION = "2.0"


class VerificationStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    DISPUTED = "disputed"
    UNAVAILABLE = "unavailable"


class ReviewStatus(StrEnum):
    UNREVIEWED = "unreviewed"
    ACCEPTED_FOR_FOLLOW_UP = "accepted_for_follow_up"
    NEEDS_INVESTIGATION = "needs_investigation"
    UNRESOLVED = "unresolved"


class InjectedErrorKind(StrEnum):
    REVERSED_DIRECTION = "reversed_direction"
    WRONG_SECTION_COUNT = "wrong_section_count"
    WRONG_DATASET_REFERENCE = "wrong_dataset_reference"
    CHANGED_EFFECT = "changed_effect"
    FIGURE_LABEL_MISMATCH = "figure_label_mismatch"
    MISSTATED_SPATIAL_PATTERN = "misstated_spatial_pattern"
    MISSING_REQUIRED_CONTROL = "missing_required_control"


class InjectedError(Contract):
    """Whether this claim is a deliberately altered copy used to test verification. Always shown when true."""

    is_injected: bool = False
    kind: InjectedErrorKind | None = None


class FindingRef(Contract):
    """The one finding a claim cites."""

    finding_id: str
    finding_kind: FindingKind


class CitedNumber(Contract):
    """One number the claim's text uses, and the field of the cited finding it comes from."""

    value: int | float | None
    source: str


class ClaimControls(Contract):
    """Ids of the controls the claim cites; a required control that is missing fails verification."""

    random_thinning: str | None = None
    label_sensitivity: str | None = None


class ClaimDraft(Contract):
    """The claim-drafting model's structured output: the sentence and every number it uses."""

    text: str
    cited: dict[str, CitedNumber]


ClaimDirection = Literal["holds", "drops"]
"""What an audit claim says the pooled observed value does under the stricter primary conditions: holds at or above
the home-matched expectation x 2^-0.5 under every one, or drops below it under at least one."""

NeighbourPattern = Literal["excluded_nearer_home", "excluded_not_nearer_home"]
"""What a claim says about Panel B's section: whether the excluded molecules are more often closer to a cell of their
gene's home type than to their own cell's centroid (a higher neighbour-proximity share) than the retained ones."""


class Claim(Contract):
    schema_version: str = CLAIM_SCHEMA_VERSION
    claim_id: str
    version: int = 1
    investigation_id: str
    dataset_id: str
    finding: FindingRef
    text: str
    cited: dict[str, CitedNumber]
    controls: ClaimControls = Field(default_factory=ClaimControls)
    figure_id: str | None = None
    evidence_status: EvidenceStatus
    verification_status: VerificationStatus = VerificationStatus.PENDING
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED
    injected: InjectedError = Field(default_factory=InjectedError)
    direction: ClaimDirection | None = Field(
        default=None, description="The direction the claim states, when it states one in structured form; else read from its text."
    )
    neighbour_pattern: NeighbourPattern | None = Field(default=None, description="The neighbour pattern the claim states, if any.")
