"""Dataset store: loads sections into validated molecule and cell tables.

Ticket 01 serves the committed synthetic section only; ticket 02 adds the GSE286184 loader.
"""

from .store import DatasetStore, UnknownDataset, UnknownSection
from .tables import CELL_COLUMNS, MOLECULE_COLUMNS, SectionTables, make_section
from .validation import MalformedSection, ValidatedSection, validate_section

__all__ = [
    "CELL_COLUMNS",
    "MOLECULE_COLUMNS",
    "DatasetStore",
    "MalformedSection",
    "ValidatedSection",
    "validate_section",
    "SectionTables",
    "UnknownDataset",
    "UnknownSection",
    "make_section",
]
