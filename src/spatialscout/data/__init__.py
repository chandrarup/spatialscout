"""Dataset store: loads sections into validated molecule and cell tables.

It serves the committed synthetic section SYN-01 and the 22 GSE286184 sections (`gse286184.py`: download,
validation, the frozen label rules in `label_rules.py`, and the committed manifest and capability report).
"""

from .store import DatasetStore, SectionNotIngested, UnknownDataset, UnknownLabelRule, UnknownSection
from .tables import CELL_COLUMNS, MOLECULE_COLUMNS, SectionTables, make_section
from .label_rules import (
    FULL_PANEL_RULE,
    LABEL_RULES,
    NPHS1_ANCHORED_RULE,
    apply_label_rules,
    label_counts,
    pool_gene_scales,
    rule_specs,
)
from .validation import MalformedSection, ValidatedSection, validate_section

__all__ = [
    "FULL_PANEL_RULE",
    "LABEL_RULES",
    "NPHS1_ANCHORED_RULE",
    "apply_label_rules",
    "label_counts",
    "pool_gene_scales",
    "rule_specs",
    "CELL_COLUMNS",
    "MOLECULE_COLUMNS",
    "DatasetStore",
    "SectionNotIngested",
    "UnknownLabelRule",
    "MalformedSection",
    "ValidatedSection",
    "validate_section",
    "SectionTables",
    "UnknownDataset",
    "UnknownSection",
    "make_section",
]
