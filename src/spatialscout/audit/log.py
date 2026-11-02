"""The audit log: an append-only JSONL file of hash-linked entries, one file per investigation.

Each line is the canonical JSON of one entry. `entry_hash` is the sha256 of the canonical JSON of the entry
without `entry_hash` (and with `prev_hash`); the first entry links to the genesis hash, 64 zeros. Edits
are detectable, not prevented: the log is tamper-evident, never tamper-proof.
"""

import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from ..contracts import GENESIS_HASH, SCHEMA_VERSION, AuditEntry, AuditEntryKind, ChainCheckResult, canonical_json, sha256_hex


class AuditLog:
    def __init__(self, path: Path, investigation_id: str, clock: Callable[[], datetime]) -> None:
        self._path = path
        self._investigation_id = investigation_id
        self._clock = clock
        self._count = 0
        self._head = GENESIS_HASH
        if path.exists():
            check = verify_chain(path.read_text(encoding="utf-8"))
            if not check.ok:
                raise ValueError(f"audit log {path} fails its chain check: {check.reason}")
            self._count, self._head = check.entries, check.head_hash or GENESIS_HASH

    @property
    def path(self) -> Path:
        return self._path

    @property
    def entries(self) -> int:
        return self._count

    @property
    def head_hash(self) -> str | None:
        return self._head if self._count else None

    def append(self, kind: AuditEntryKind, payload: dict[str, Any]) -> AuditEntry:
        body = {
            "schema_version": SCHEMA_VERSION,
            "seq": self._count + 1,
            "investigation_id": self._investigation_id,
            "recorded_at": self._clock().isoformat(),
            "kind": kind,
            "payload": payload,
            "prev_hash": self._head,
        }
        entry_hash = sha256_hex(canonical_json(body))
        with self._path.open("a", encoding="utf-8") as log_file:
            log_file.write(canonical_json({**body, "entry_hash": entry_hash}) + "\n")
        self._count, self._head = self._count + 1, entry_hash
        return AuditEntry.model_validate({**body, "entry_hash": entry_hash})

    def text(self) -> str:
        return self._path.read_text(encoding="utf-8") if self._path.exists() else ""


def verify_chain(jsonl: str) -> ChainCheckResult:
    """Check every entry's hash and link. Works on the raw JSON, so any edit to any field is caught."""
    head = GENESIS_HASH
    count = 0
    for line in jsonl.splitlines():
        seq = count + 1
        try:
            entry = json.loads(line)
            if not isinstance(entry, dict):
                return _broken(count, head, seq, f"entry {seq} is not a JSON object")
            stored = entry.pop("entry_hash", None)
            if entry.get("seq") != seq:
                return _broken(count, head, seq, f"entry {seq} is missing or out of order")
            if entry.get("prev_hash") != head:
                return _broken(count, head, seq, f"entry {seq} does not link to the entry before it")
            if sha256_hex(canonical_json(entry)) != stored:
                return _broken(count, head, seq, f"entry {seq} does not match its hash: it was edited")
        except ValueError:
            return _broken(count, head, seq, f"entry {seq} is not valid canonical JSON")
        head, count = stored, seq
    return ChainCheckResult(ok=True, entries=count, head_hash=head if count else None)


def _broken(count: int, head: str, seq: int, reason: str) -> ChainCheckResult:
    return ChainCheckResult(ok=False, entries=count, head_hash=head if count else None, first_bad_seq=seq, reason=reason)
