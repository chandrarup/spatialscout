"""The base every contract shares, plus canonical JSON and ids.

Pydantic models are the single source of truth for SpatialScout's data contracts. JSON Schema is
generated from them, and the web app's TypeScript types are generated from that (see `schema.py`).
"""

import hashlib
import json
import secrets
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

SCHEMA_VERSION = "1.0"


class Contract(BaseModel):
    """Base for every contract. Unknown fields are rejected, so a typo never passes silently."""

    model_config = ConfigDict(extra="forbid", json_schema_serialization_defaults_required=True)


def canonical_json(value: Any) -> str:
    """Canonical JSON: sorted keys, no whitespace, UTF-8 text, and no NaN or Infinity (they are not JSON)."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def new_id(prefix: str) -> str:
    """A random id such as `inv-3f9a1c0b7e2d`, for things that happen once (investigations, claims)."""
    return f"{prefix}-{secrets.token_hex(6)}"


def checksum(model: BaseModel) -> str:
    """sha256 of a model's canonical JSON: the artifact checksum used in cache keys and the plan hash."""
    return sha256_hex(canonical_json(model.model_dump(mode="json")))


def content_id(prefix: str, payload: Any) -> str:
    """A content-addressed id: the same payload always gets the same id, so artifacts are immutable."""
    return f"{prefix}-{sha256_hex(canonical_json(payload))[:16]}"


class ConditionName(StrEnum):
    """An assignment condition: a rule that decides which molecules count toward a cell (ADR-0002)."""

    DEFAULT = "default"
    NUCLEUS_ONLY = "nucleus_only"
    DISTANCE_CAP_1UM = "distance_cap_1um"
    DISTANCE_CAP_2UM = "distance_cap_2um"
    STRUCTURE_CONSTRAINED = "structure_constrained"


class EvidenceStatus(StrEnum):
    """An evidence label. It says what the evidence supports, never whether a finding is biologically true."""

    STABLE = "stable"
    SEGMENTATION_SENSITIVE = "segmentation_sensitive"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


FindingKind = Literal["audit", "contrast"]

RunMode = Literal["immutable_replay", "cached_tool_rerun", "live"]
"""How an investigation gets its results:
- immutable_replay: streams a recorded investigation's events verbatim, with their original timestamps;
- cached_tool_rerun: re-runs the deterministic tools and takes model responses from storage;
- live: fresh model calls (gated; arrives with ticket 03)."""


class Contrast(Contract):
    """One disease group compared with the control group, for example DKD vs Control."""

    disease: str
    control: str
