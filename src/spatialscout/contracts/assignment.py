"""Assignment audit contracts: what a condition keeps and what it excludes."""

from pydantic import Field

from .base import SCHEMA_VERSION, ConditionName, Contract


class AuditMetrics(Contract):
    """Retention and excluded molecules for one scope of a section under one assignment condition.

    A scope is the whole section (cell_type and gene are null), one cell type (gene is null), or one gene
    within one cell type. Retention is the share of default-condition molecules the condition keeps; it is
    null, with a reason, when the scope has no default-condition molecules.
    """

    section_id: str
    condition: ConditionName
    cell_type: str | None
    gene: str | None
    default_molecules: int
    kept_molecules: int
    excluded_molecules: int
    retention: float | None
    retention_missing_reason: str | None = None


class SectionAudit(Contract):
    """The output artifact of the `audit_section` tool."""

    schema_version: str = SCHEMA_VERSION
    artifact_id: str
    dataset_id: str
    section_id: str
    conditions: list[ConditionName]
    metrics: list[AuditMetrics] = Field(default_factory=list)
    excluded_molecule_ids: dict[ConditionName, list[str]]
