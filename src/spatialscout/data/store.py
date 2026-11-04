"""The dataset store: loads a dataset's sections into validated tables, with its manifest and capability report.

Two datasets sit behind one interface:

- `synthetic`, the committed fixture in `fixtures/synthetic/` (section SYN-01);
- `GSE286184`, served when `artifacts/GSE286184/` holds its manifest, capability report and label rules. Its
  validated tables live in the processed directory written by `spatialscout ingest` (`make data`); without
  them the manifest and report are still served, and loading a section raises `SectionNotIngested`.

A GSE286184 section is labelled under either frozen label rule: `load_section(section_id, label_rule_id)`, with
the full-panel rule as the default. The cells are the same under both rules; only `cell_type` differs.
"""

import hashlib
import json
from functools import cached_property
from pathlib import Path

import pandas as pd

from ..contracts import CapabilityReport, DatasetManifest, FileChecksum, LabelRuleSet, SectionInfo, StructureMask, StructureRun
from .gse286184 import DATASET_ID as GSE286184, label_column
from .tables import SectionTables, make_section

SYNTHETIC = "synthetic"


class UnknownDataset(KeyError):
    """The store has no dataset with this id."""


class UnknownSection(KeyError):
    """No dataset in the store has a section with this id."""


class UnknownLabelRule(KeyError):
    """The section's dataset has no frozen label rule with this id."""


class SectionNotIngested(FileNotFoundError):
    """The section is in the manifest, but its validated tables have not been built here (run `make data`)."""


class DatasetStore:
    """Loads sections by id and caches them; tables are read once and never modified."""

    def __init__(self, fixtures_dir: Path, *, artifacts_dir: Path | None = None, processed_dir: Path | None = None) -> None:
        self._synthetic_dir = Path(fixtures_dir) / "synthetic"
        self._gse_artifacts = Path(artifacts_dir) / GSE286184 if artifacts_dir else None
        self._processed_dir = Path(processed_dir) if processed_dir else None
        self._sections: dict[tuple[str, str], SectionTables] = {}

    # --- datasets ------------------------------------------------------------------------------------------

    def dataset_ids(self) -> list[str]:
        has_gse = self._gse_artifacts is not None and (self._gse_artifacts / "manifest.json").is_file()
        return ([GSE286184] if has_gse else []) + [SYNTHETIC]

    def sections(self, dataset_id: str) -> list[SectionInfo]:
        return self.manifest(dataset_id).sections

    def distinct_sections(self, dataset_id: str) -> list[SectionInfo]:
        """The sections to count in any cross-section analysis: a section whose raw content duplicates an earlier
        one (`duplicate_of`) is left out, so each distinct section counts once."""
        return [s for s in self.sections(dataset_id) if s.duplicate_of is None]

    def dataset_of(self, section_id: str) -> str:
        for dataset_id in self.dataset_ids():
            if any(s.section_id == section_id for s in self.sections(dataset_id)):
                return dataset_id
        raise UnknownSection(section_id)

    def section_info(self, section_id: str) -> SectionInfo:
        return next(s for s in self.sections(self.dataset_of(section_id)) if s.section_id == section_id)

    def capability_report(self, dataset_id: str) -> CapabilityReport:
        self._check(dataset_id)
        if dataset_id == GSE286184:
            return self._gse_report
        return CapabilityReport(dataset_id=dataset_id, checks=self._synthetic_info["capabilities"])

    def manifest(self, dataset_id: str) -> DatasetManifest:
        self._check(dataset_id)
        if dataset_id == GSE286184:
            return self._gse_manifest
        return self._synthetic_manifest

    def label_rules(self, dataset_id: str) -> LabelRuleSet | None:
        """The frozen label rules with their per-section counts; None for the synthetic dataset, whose labels
        are given by construction."""
        self._check(dataset_id)
        return self._gse_label_rules if dataset_id == GSE286184 else None

    # --- sections ------------------------------------------------------------------------------------------

    def load_section(self, section_id: str, label_rule_id: str | None = None) -> SectionTables:
        dataset_id = self.dataset_of(section_id)
        if dataset_id == SYNTHETIC:
            rule = self._synthetic_info["label_rule_id"]
            if label_rule_id not in (None, rule):
                raise UnknownLabelRule(label_rule_id)
        else:
            rules = self._gse_label_rules
            rule = label_rule_id or rules.default_label_rule_id
            if rule not in {r.label_rule_id for r in rules.rules}:
                raise UnknownLabelRule(rule)
        key = (section_id, rule)
        if key not in self._sections:
            self._sections[key] = (
                self._read_synthetic_section(section_id) if dataset_id == SYNTHETIC else self._read_gse_section(section_id, rule)
            )
        return self._sections[key]

    # --- GSE286184 -----------------------------------------------------------------------------------------

    @cached_property
    def _gse_manifest(self) -> DatasetManifest:
        return DatasetManifest.model_validate_json(self._gse_artifact("manifest.json"))

    @cached_property
    def _gse_report(self) -> CapabilityReport:
        return CapabilityReport.model_validate_json(self._gse_artifact("capability_report.json"))

    @cached_property
    def _gse_label_rules(self) -> LabelRuleSet:
        return LabelRuleSet.model_validate_json(self._gse_artifact("label_rules.json"))

    def _gse_artifact(self, name: str) -> str:
        assert self._gse_artifacts is not None
        return (self._gse_artifacts / name).read_text(encoding="utf-8")

    def _read_gse_section(self, section_id: str, label_rule_id: str) -> SectionTables:
        directory = self._processed_dir / section_id if self._processed_dir else None
        if directory is None or not (directory / "cells.parquet").is_file():
            raise SectionNotIngested(
                f"section {section_id} has no validated tables here; run `make data` to download and ingest GSE286184"
            )
        molecules = pd.read_parquet(directory / "molecules.parquet")
        cells = pd.read_parquet(directory / "cells.parquet")
        cells["cell_type"] = cells[label_column(label_rule_id)]
        return make_section(
            section_id, GSE286184, label_rule_id=label_rule_id, molecules=molecules, cells=cells, structures=self.sam_structures(section_id)
        )

    def structure_run(self, section_id: str) -> StructureRun | None:
        """The committed SAM 3.1 structure-finder run of a GSE286184 section (exploratory, ADR-0006), if any:
        `artifacts/GSE286184/structures/<section_id>.json`, written by `spatialscout structures`."""
        path = self._gse_artifacts / "structures" / f"{section_id}.json" if self._gse_artifacts else None
        if path is None or not path.is_file():
            return None
        return StructureRun.model_validate_json(path.read_text(encoding="utf-8"))

    def sam_structures(self, section_id: str) -> list[StructureMask]:
        run = self.structure_run(section_id)
        return list(run.structures) if run else []

    # --- synthetic -----------------------------------------------------------------------------------------

    @cached_property
    def _synthetic_info(self) -> dict:
        return json.loads((self._synthetic_dir / "dataset.json").read_text(encoding="utf-8"))

    @cached_property
    def _synthetic_manifest(self) -> DatasetManifest:
        info = self._synthetic_info
        files = sorted(p for p in self._synthetic_dir.rglob("*") if p.is_file())
        return DatasetManifest(
            dataset_id=info["dataset_id"],
            title=info["title"],
            description=info["description"],
            synthetic=True,
            source_urls=[],
            download_date=None,
            coordinate_units=info["coordinate_units"],
            panel=info["panel"],
            sections=[SectionInfo.model_validate(s) for s in info["sections"]],
            files=[
                FileChecksum(path=p.relative_to(self._synthetic_dir).as_posix(), sha256=hashlib.sha256(p.read_bytes()).hexdigest(), bytes=p.stat().st_size)
                for p in files
            ],
            label_rule_ids=[info["label_rule_id"]],
        )

    def _check(self, dataset_id: str) -> None:
        if dataset_id not in self.dataset_ids():
            raise UnknownDataset(dataset_id)

    def _read_synthetic_section(self, section_id: str) -> SectionTables:
        info = self._synthetic_info
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
