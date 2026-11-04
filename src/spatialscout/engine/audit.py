"""The assignment audit of one section: what each condition keeps and excludes, relative to the default."""

from collections.abc import Sequence

import numpy as np

from ..contracts import AuditMetrics, ConditionName, SectionAudit, content_id
from ..data import SectionTables
from .conditions import inclusion_mask

NO_DEFAULT_MOLECULES = "no molecules in this scope under the default condition"

# A scope is (cell type, gene, mask of default-condition molecules in the scope); None means "all".
Scope = tuple[str | None, str | None, np.ndarray]


def audit_section(section: SectionTables, conditions: Sequence[ConditionName]) -> SectionAudit:
    """Audit a section under each condition against the default condition.

    Reports retention and excluded molecules for the whole section, for each cell type, and for each gene
    within a cell type. Molecules the default condition leaves unassigned never count.
    """
    molecule_ids = section.molecules["molecule_id"].to_numpy(dtype=object)
    default = inclusion_mask(section, ConditionName.DEFAULT)
    scopes = _scopes(section, default)
    metrics: list[AuditMetrics] = []
    excluded: dict[ConditionName, list[str]] = {}
    for condition in conditions:
        kept = default & inclusion_mask(section, condition)
        excluded[condition] = [str(m) for m in molecule_ids[default & ~kept]]
        metrics.extend(_metrics(section.section_id, condition, scope, kept) for scope in scopes)
    audit = SectionAudit(
        artifact_id="pending",
        dataset_id=section.dataset_id,
        section_id=section.section_id,
        conditions=list(conditions),
        metrics=metrics,
        excluded_molecule_ids=excluded,
    )
    return audit.model_copy(update={"artifact_id": content_id("art", audit.model_dump(mode="json", exclude={"artifact_id"}))})


def _scopes(section: SectionTables, default: np.ndarray) -> list[Scope]:
    cells = section.cells
    cell_type_of = dict(zip(cells["cell_id"].astype(str), cells["cell_type"].astype(str), strict=True))
    molecule_cell_types = section.molecules["cell_id"].map(cell_type_of).astype("string").fillna("").to_numpy(dtype=object)
    genes = section.molecules["gene"].astype(str).to_numpy(dtype=object)
    scopes: list[Scope] = [(None, None, default)]
    for cell_type in sorted(set(cell_type_of.values())):
        in_type = default & (molecule_cell_types == cell_type)
        scopes.append((cell_type, None, in_type))
        scopes.extend((cell_type, gene, in_type & (genes == gene)) for gene in sorted(set(genes[in_type])))
    return scopes


def _metrics(section_id: str, condition: ConditionName, scope: Scope, kept: np.ndarray) -> AuditMetrics:
    cell_type, gene, in_scope = scope
    n_default = int(in_scope.sum())
    n_kept = int((in_scope & kept).sum())
    return AuditMetrics(
        section_id=section_id,
        condition=condition,
        cell_type=cell_type,
        gene=gene,
        default_molecules=n_default,
        kept_molecules=n_kept,
        excluded_molecules=n_default - n_kept,
        retention=n_kept / n_default if n_default else None,
        retention_missing_reason=None if n_default else NO_DEFAULT_MOLECULES,
    )
