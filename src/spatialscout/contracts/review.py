"""Verification and review contracts. Shallow until tickets 10 (verification) and 11 (review) fill them."""

from datetime import datetime
from typing import Literal

from .base import SCHEMA_VERSION, Contract
from .claim import VerificationStatus


class CheckResult(Contract):
    kind: Literal["structural", "numerical", "visual"]
    status: Literal["passed", "failed", "disputed", "unavailable"]
    details: str


class VerificationResult(Contract):
    """Every check run on one claim version, and the verification status they add up to."""

    schema_version: str = SCHEMA_VERSION
    claim_id: str
    claim_version: int
    checks: list[CheckResult]
    verification_status: VerificationStatus


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
