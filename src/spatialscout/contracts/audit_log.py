"""Audit log contracts: append-only, hash-linked entries (tamper-evident, never tamper-proof).

Each entry's `entry_hash` is the sha256 of the canonical JSON of the entry without `entry_hash` (and with
`prev_hash`). The first entry's `prev_hash` is the genesis hash, 64 zeros.
"""

from datetime import datetime
from typing import Any, Literal

from .base import SCHEMA_VERSION, Contract

GENESIS_HASH = "0" * 64

AuditEntryKind = Literal[
    "investigation_started",
    "model_call",
    "plan_proposed",
    "plan_approved",
    "tool_call",
    "claim_drafted",
    "package_exported",
    "error",
]


class AuditEntry(Contract):
    schema_version: str = SCHEMA_VERSION
    seq: int
    investigation_id: str
    recorded_at: datetime
    kind: AuditEntryKind
    payload: dict[str, Any]
    prev_hash: str
    entry_hash: str


class ChainCheckResult(Contract):
    """The outcome of checking an audit log's hash chain. `first_bad_seq` is the first entry that fails."""

    ok: bool
    entries: int
    head_hash: str | None
    first_bad_seq: int | None = None
    reason: str | None = None
