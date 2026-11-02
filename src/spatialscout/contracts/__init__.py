"""SpatialScout data contracts. Pydantic models here are the single source of truth for every shape
that crosses a module or the HTTP boundary; TypeScript types are generated from them."""

from .assignment import AuditMetrics, SectionAudit
from .base import SCHEMA_VERSION, ConditionName, Contract, canonical_json, content_id, new_id, sha256_hex

__all__ = [
    "SCHEMA_VERSION",
    "AuditMetrics",
    "ConditionName",
    "Contract",
    "SectionAudit",
    "canonical_json",
    "content_id",
    "new_id",
    "sha256_hex",
]
