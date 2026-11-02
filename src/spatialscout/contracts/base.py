"""The base every contract shares, plus canonical JSON and ids.

Pydantic models are the single source of truth for SpatialScout's data contracts. JSON Schema is
generated from them, and the web app's TypeScript types are generated from that (see `schema.py`).
"""

import hashlib
import json
import secrets
from enum import StrEnum
from typing import Any

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
