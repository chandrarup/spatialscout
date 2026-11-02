"""The dataset store: loads a dataset's sections into validated tables.

Ticket 01 serves the committed synthetic dataset in `fixtures/synthetic/`; ticket 02 adds GSE286184
from raw GEO files behind the same interface.
"""

import json
from pathlib import Path

import pandas as pd

from ..contracts import StructureMask
from .tables import SectionTables, make_section


class UnknownSection(KeyError):
    """No dataset in the store has a section with this id."""


class DatasetStore:
    """Loads sections by id and caches them; tables are read once and never modified."""

    def __init__(self, fixtures_dir: Path) -> None:
        self._synthetic_dir = Path(fixtures_dir) / "synthetic"
        self._sections: dict[str, SectionTables] = {}

    def load_section(self, section_id: str) -> SectionTables:
        if section_id not in self._sections:
            self._sections[section_id] = self._read_synthetic_section(section_id)
        return self._sections[section_id]

    def _dataset_info(self) -> dict:
        return json.loads((self._synthetic_dir / "dataset.json").read_text())

    def _read_synthetic_section(self, section_id: str) -> SectionTables:
        info = self._dataset_info()
        if section_id not in {s["section_id"] for s in info["sections"]}:
            raise UnknownSection(section_id)
        directory = self._synthetic_dir / section_id
        text_columns = {"molecule_id": "string", "gene": "string", "cell_id": "string", "cell_type": "string"}
        molecules = pd.read_csv(directory / "molecules.csv", dtype=text_columns)
        cells = pd.read_csv(directory / "cells.csv", dtype=text_columns)
        structures = [StructureMask.model_validate(s) for s in json.loads((directory / "structures.json").read_text())]
        return make_section(
            section_id,
            info["dataset_id"],
            label_rule_id=info["label_rule_id"],
            molecules=molecules,
            cells=cells,
            structures=structures,
        )
