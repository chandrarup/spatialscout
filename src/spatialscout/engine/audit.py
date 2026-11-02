"""The assignment audit of one section: what each condition keeps and excludes, relative to the default."""

from collections.abc import Sequence

from ..contracts import ConditionName, SectionAudit, content_id
from ..data import SectionTables
from .conditions import inclusion_mask


def audit_section(section: SectionTables, conditions: Sequence[ConditionName]) -> SectionAudit:
    """Audit a section under each condition against the default condition."""
    molecule_ids = section.molecules["molecule_id"].to_numpy()
    default = inclusion_mask(section, ConditionName.DEFAULT)
    excluded: dict[ConditionName, list[str]] = {}
    for condition in conditions:
        kept = default & inclusion_mask(section, condition)
        excluded[condition] = [str(m) for m in molecule_ids[default & ~kept]]
    body = {
        "dataset_id": section.dataset_id,
        "section_id": section.section_id,
        "conditions": list(conditions),
        "excluded_molecule_ids": excluded,
    }
    return SectionAudit(artifact_id=content_id("art", SectionAudit.model_construct(**body).model_dump(mode="json", exclude={"artifact_id"})), **body)
