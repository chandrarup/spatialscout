"""Control contracts: the required controls a claim cites (`Claim.controls`), each with a `ctl-` id.

- The random-thinning control compares an audit result's observed values with what random molecule loss at a
  matched rate would give: cell-matched and home-matched expectations, the excess drop against each, and the
  verdict per stricter condition under the frozen audit label rule.
- The label-sensitivity check reports one measure of one population under two label rules, one of which does not
  use the finding's genes, with the cell counts under each and how many cells the rules disagree on.
"""

from typing import Literal

from pydantic import Field

from .base import SCHEMA_VERSION, ConditionName, Contract, EvidenceStatus
from .finding import AuditSectionValues, PooledConditionValue


class RandomThinningControl(Contract):
    schema_version: str = SCHEMA_VERSION
    control_kind: Literal["random_thinning"] = "random_thinning"
    control_id: str
    finding_id: str
    dataset_id: str
    label_rule_id: str
    cell_type: str
    genes: list[str]
    measure: str
    eligible_section_ids: list[str]
    pooled: list[PooledConditionValue]
    sections: list[AuditSectionValues] = Field(description="Every section's values; only eligible ones are pooled.")
    threshold: str = Field(description="The frozen audit threshold the verdict uses.")
    conditions_below_threshold: list[ConditionName]
    label: EvidenceStatus
    label_reason: str


class LabelRuleArm(Contract):
    """The measure under one label rule."""

    label_rule_id: str
    finding_id: str
    cells_labelled: int = Field(description="Cells of the population summed over every counted section.")
    cells_labelled_by_section: dict[str, int]
    eligible_section_ids: list[str]
    pooled: list[PooledConditionValue]
    label: EvidenceStatus
    label_reason: str


class LabelSensitivityCheck(Contract):
    schema_version: str = SCHEMA_VERSION
    control_kind: Literal["label_sensitivity"] = "label_sensitivity"
    control_id: str
    dataset_id: str
    cell_type: str
    genes: list[str]
    measure: str
    arms: list[LabelRuleArm] = Field(min_length=2, max_length=2)
    cells_in_both: int = Field(description="Cells labelled with the population under both rules.")
    cells_only_first: int
    cells_only_second: int
    same_label: bool = Field(description="Both rules give the same evidence label.")
    summary: str
