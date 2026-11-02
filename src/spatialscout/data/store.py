"""The dataset store: loads a dataset's sections into validated tables, with its manifest and capability report.

Ticket 01 serves the committed synthetic dataset in `fixtures/synthetic/`; ticket 02 adds GSE286184
from raw GEO files behind the same interface.
"""

import hashlib
import json
from functools import cached_property
from pathlib import Path

import pandas as pd

from ..contracts import CapabilityReport, DatasetManifest, FileChecksum, SectionInfo, StructureMask
from .tables import SectionTables, make_section


class UnknownDataset(KeyError):
    """The store has no dataset with this id."""


class UnknownSection(KeyError):
    """No dataset in the store has a section with this id."""


class DatasetStore:
    """Loads sections by id and caches them; tables are read once and never modified."""

    def __init__(self, fixtures_dir: Path) -> None:
        self._synthetic_dir = Path(fixtures_dir) / "synthetic"
        self._sections: dict[str, SectionTables] = {}

    @cached_property
    def _info(self) -> dict:
        return json.loads((self._synthetic_dir / "dataset.json").read_text(encoding="utf-8"))

    def dataset_ids(self) -> list[str]:
        return [self._info["dataset_id"]]

    def sections(self, dataset_id: str) -> list[SectionInfo]:
        self._check(dataset_id)
        return [SectionInfo.model_validate(s) for s in self._info["sections"]]

    def load_section(self, section_id: str) -> SectionTables:
        if section_id not in self._sections:
            self._sections[section_id] = self._read_synthetic_section(section_id)
        return self._sections[section_id]

    def capability_report(self, dataset_id: str) -> CapabilityReport:
        self._check(dataset_id)
        return CapabilityReport(dataset_id=dataset_id, checks=self._info["capabilities"])

    def manifest(self, dataset_id: str) -> DatasetManifest:
        self._check(dataset_id)
        info = self._info
        files = sorted(p for p in self._synthetic_dir.rglob("*") if p.is_file())
        return DatasetManifest(
            dataset_id=dataset_id,
            title=info["title"],
            description=info["description"],
            synthetic=True,
            source_urls=[],
            download_date=None,
            coordinate_units=info["coordinate_units"],
            panel=info["panel"],
            sections=self.sections(dataset_id),
            files=[
                FileChecksum(path=p.relative_to(self._synthetic_dir).as_posix(), sha256=hashlib.sha256(p.read_bytes()).hexdigest(), bytes=p.stat().st_size)
                for p in files
            ],
        )

    def _check(self, dataset_id: str) -> None:
        if dataset_id not in self.dataset_ids():
            raise UnknownDataset(dataset_id)

    def _read_synthetic_section(self, section_id: str) -> SectionTables:
        info = self._info
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
