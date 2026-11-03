"""GSE286184: 22 Xenium sections of human kidney (Control, DKD, IgAN, MCD, MN), from raw GEO files to validated
tables and the committed manifest, capability report and label rules.

    uv run spatialscout ingest        # or `make data`

downloads any missing raw file into the raw directory, validates every section, freezes the label rules and
writes the validated tables to the processed directory (both git-ignored, under `data/`). The small derived
artifacts go to `artifacts/GSE286184/` and are committed. Every step is idempotent: a rerun on the same raw files
reuses the validated tables and rewrites byte-identical artifacts.

Section groups come from GEO's `condition:` field. GEO does not map sections to donors; the donor counts are the
paper's published counts and donors are never inferred from expression (ADR-0007).
"""

import gzip
import hashlib
import io
import json
import shutil
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from ..contracts import (
    CapabilityCheck,
    CapabilityReport,
    ContrastEligibility,
    Contrast,
    DatasetFilters,
    DatasetManifest,
    FileChecksum,
    LabelRuleSet,
    SectionInfo,
    SectionValidation,
)
from .label_rules import FULL_PANEL_RULE, LABEL_RULES, apply_label_rules, label_counts, pool_gene_scales, rule_specs
from .validation import MIN_QV, validate_section

DATASET_ID = "GSE286184"
SERIES_URL = "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE286184"
PAPER_URL = "https://pmc.ncbi.nlm.nih.gov/articles/PMC13586693/"
CITATION = (
    "Xenium in situ data from NCBI GEO series GSE286184 (22 human kidney sections: Control, DKD, IgAN, MCD, MN), "
    f"{SERIES_URL}; associated paper {PAPER_URL}. Cell type labels are SpatialScout's own marker-rule labels, "
    "not the authors' annotation, which was not deposited."
)
RAW_KINDS = ("transcripts.parquet.gz", "cells.csv.gz", "features.tsv.gz")
INGEST_VERSION = "2"
"""Bump when validation or labelling changes, so a rerun rebuilds the validated tables."""

CONTROL = "Control"
GROUP_OF_SECTION: dict[int, str] = {
    **{n: CONTROL for n in (1, 2, 6)},
    **{n: "DKD" for n in (3, 4, 5, 7, 8, 9)},
    **{n: "IgAN" for n in (10, 11, 12, 13)},
    **{n: "MCD" for n in (14, 15, 16, 17)},
    **{n: "MN" for n in (18, 19, 20, 21, 22)},
}
DONORS_PUBLISHED = {CONTROL: 3, "DKD": 5, "IgAN": 4, "MCD": 3, "MN": 4}
"""Patients per group from the paper (19 in all); GEO gives no section-to-donor mapping."""
DONOR_CAVEAT = (
    "GEO lists 22 samples; the paper reports 19 donors (Control 3, DKD 5, IgAN 4, MCD 3, MN 4). GEO does not say "
    "which sections share a donor; DKD, MCD and MN each hold one repeat-donor section, and samples with identical "
    "files are listed under distinct_sections. Sections are not independent donors, and donors are never inferred "
    "from expression."
)


@dataclass(frozen=True)
class Section:
    number: int

    @property
    def section_id(self) -> str:
        return f"GSM{8720408 + self.number}"

    @property
    def name(self) -> str:
        return f"x{self.number}"

    @property
    def group(self) -> str:
        return GROUP_OF_SECTION[self.number]

    def file_name(self, kind: str) -> str:
        return f"{self.section_id}_kidney_xenium_{self.number}_{kind}"

    def url(self, kind: str) -> str:
        return f"https://ftp.ncbi.nlm.nih.gov/geo/samples/GSM8720nnn/{self.section_id}/suppl/{self.file_name(kind)}"


SECTIONS = tuple(Section(n) for n in sorted(GROUP_OF_SECTION))
SECTION_BY_ID = {s.section_id: s for s in SECTIONS}
CONTROL_SECTION_IDS = [s.section_id for s in SECTIONS if s.group == CONTROL]


# --- Capability report ---------------------------------------------------------------------------------------


def capability_report(duplicates: dict[str, str] | None = None) -> CapabilityReport:
    """`duplicates` maps a section to an earlier section with identical raw content (found by ingest)."""
    duplicates = duplicates or {}
    checks = [
        CapabilityCheck(
            capability="coordinate_inspection",
            status="supported",
            reason="Every molecule and cell centroid has a position in micrometres; the viewer opens any section whole.",
        ),
        CapabilityCheck(
            capability="assignment_audit",
            status="supported",
            reason=(
                "Molecules carry cell_id, overlaps_nucleus and nucleus_distance, so default, nucleus-only and distance-cap "
                "conditions come from molecule flags (ADR-0002)."
            ),
        ),
        CapabilityCheck(
            capability="disease_contrast",
            status="supported",
            reason=(
                "Descriptive only: per-section values and effects for DKD, IgAN, MCD and MN against Control, with no "
                "p-values or confidence intervals, because GEO's 22 samples hold "
                f"{len(SECTIONS) - len(duplicates)} distinct sections from 19 published donors with no published mapping "
                "(ADR-0007). See each contrast's inference eligibility."
            ),
        ),
        CapabilityCheck(
            capability="cell_boundaries",
            status="unavailable",
            reason="No cell or nucleus boundary polygons were deposited; the viewer draws nuclei as circles from nucleus area, an approximation.",
        ),
        CapabilityCheck(
            capability="images",
            status="unavailable",
            reason="No morphology (DAPI) or H&E images were deposited, so structure outlines must come from an image rendered from the data itself.",
        ),
        CapabilityCheck(
            capability="deposited_cell_type_labels",
            status="unavailable",
            reason="The authors annotated cells in Seurat but did not deposit labels; SpatialScout labels cells with its own frozen marker rules.",
        ),
        CapabilityCheck(
            capability="donor_mapping",
            status="unavailable",
            reason=DONOR_CAVEAT,
        ),
        _distinct_sections(duplicates),
    ]
    return CapabilityReport(dataset_id=DATASET_ID, checks=checks, contrasts=[_contrast(g, duplicates) for g in ("DKD", "IgAN", "MCD", "MN")])


def _distinct_sections(duplicates: dict[str, str]) -> CapabilityCheck:
    distinct = len(SECTIONS) - len(duplicates)
    pairs = "; ".join(f"{dup} ({SECTION_BY_ID[dup].name}) holds the same content as {orig} ({SECTION_BY_ID[orig].name})" for dup, orig in duplicates.items())
    return CapabilityCheck(
        capability="distinct_sections",
        status="supported",
        reason=(
            f"{distinct} distinct sections among {len(SECTIONS)} GEO samples, found by comparing checksums of the decompressed raw files"
            + (f": {pairs}. Every analysis counts each pair once; the copy stays listed in the manifest as a duplicate." if pairs else ".")
        ),
    )


def _contrast(disease: str, duplicates: dict[str, str]) -> ContrastEligibility:
    disease_ids = [s.section_id for s in SECTIONS if s.group == disease]
    excluded = [sid for sid in disease_ids + CONTROL_SECTION_IDS if sid in duplicates]
    distinct = len(disease_ids) - sum(sid in duplicates for sid in disease_ids)
    donors = DONORS_PUBLISHED[disease]
    if distinct < len(disease_ids) and distinct < donors:
        distinctness, statement = (
            "counts_do_not_reconcile",
            f"not shown donor-distinct: GEO's {len(disease_ids)} {disease} samples hold {distinct} distinct sections against "
            f"{donors} published {disease} patients, so the published counts no longer reconcile with the deposit",
        )
    elif donors == len(disease_ids):
        distinctness, statement = (
            "conditionally_donor_distinct_unconfirmed",
            "conditionally donor-distinct by published counts, unconfirmed",
        )
    else:
        distinctness, statement = (
            "repeat_donor_in_group",
            f"{len(disease_ids)} sections from {donors} donors: one donor contributes two sections, and GEO does not say which",
        )
    return ContrastEligibility(
        groups=Contrast(disease=disease, control=CONTROL),
        disease_section_ids=[sid for sid in disease_ids if sid not in excluded],
        control_section_ids=[sid for sid in CONTROL_SECTION_IDS if sid not in excluded],
        disease_donors_published=donors,
        control_donors_published=DONORS_PUBLISHED[CONTROL],
        donor_distinctness=distinctness,
        donor_distinctness_statement=statement,
        inference_reason=(
            "Descriptive only: GEO does not map sections to donors, so sections cannot be treated as independent "
            "replicates and no p-value or confidence interval is reported (ADR-0007)."
            + "".join(
                f" {sid} is left out: its raw files hold the same content as {duplicates[sid]}, so counting both would "
                "count one section twice."
                for sid in excluded
            )
        ),
        excluded_section_ids=excluded,
    )


# --- Download ------------------------------------------------------------------------------------------------


def download_missing(raw_dir: Path, log: Callable[[str], None] = print) -> int:
    """Fetch every raw file that is missing or empty. Returns how many were downloaded."""
    fetched = 0
    for section in SECTIONS:
        directory = raw_dir / section.section_id
        directory.mkdir(parents=True, exist_ok=True)
        for kind in RAW_KINDS:
            target = directory / section.file_name(kind)
            if target.is_file() and target.stat().st_size > 0:
                continue
            log(f"downloading {section.url(kind)}")
            partial = target.with_name(target.name + ".part")
            with urllib.request.urlopen(section.url(kind), timeout=120) as response, partial.open("wb") as out:
                shutil.copyfileobj(response, out)
            partial.replace(target)
            fetched += 1
    return fetched


# --- Ingest --------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Paths:
    raw_dir: Path
    processed_dir: Path
    artifacts_dir: Path

    def processed(self, section: Section) -> Path:
        return self.processed_dir / section.section_id


def ingest(paths: Paths, log: Callable[[str], None] = print) -> None:
    """Validate all 22 sections, freeze the label rules and write the tables and artifacts."""
    raw_files = {s.section_id: {k: _checksum(paths.raw_dir / s.section_id / s.file_name(k), paths.raw_dir) for k in RAW_KINDS} for s in SECTIONS}
    panels = {}
    validations: dict[str, SectionValidation] = {}
    contents: dict[str, str] = {}
    for section in SECTIONS:
        panels[section.section_id] = _panel(paths.raw_dir / section.section_id / section.file_name("features.tsv.gz"))
        validations[section.section_id], contents[section.section_id] = _validated(
            section, paths, raw_files[section.section_id], panels[section.section_id], log
        )
    duplicates = _duplicates(contents)
    for section_id, original in duplicates.items():
        log(f"{section_id} holds the same raw content as {original}; contrasts count only {original}")
    panel = panels[SECTIONS[0].section_id]
    differing_panels = [sid for sid, p in panels.items() if p != panel]
    if differing_panels:
        raise ValueError(f"sections with a different gene panel: {', '.join(differing_panels)}")

    gene_scales = pool_gene_scales(_read_molecules(paths.processed(SECTION_BY_ID[sid]), columns=["cell_id", "gene"]) for sid in CONTROL_SECTION_IDS)
    counts = {}
    infos = []
    for section in SECTIONS:
        directory = paths.processed(section)
        molecules = _read_molecules(directory)
        cells = pd.read_parquet(directory / "cells.validated.parquet")
        labels = apply_label_rules(molecules[["cell_id", "gene"]], list(cells["cell_id"]), gene_scales)
        for rule in LABEL_RULES:
            cells[label_column(rule)] = labels[rule].to_numpy()
        _write_parquet(cells, directory / "cells.parquet")
        counts[section.section_id] = label_counts(labels)
        xs = pd.concat([molecules["x"], cells["x"]])
        ys = pd.concat([molecules["y"], cells["y"]])
        infos.append(
            SectionInfo(
                section_id=section.section_id,
                group=section.group,
                extent=[round(float(xs.min()), 3), round(float(ys.min()), 3), round(float(xs.max()), 3), round(float(ys.max()), 3)],
                name=section.name,
                molecules=len(molecules),
                cells=len(cells),
                validation=validations[section.section_id],
                content_sha256=contents[section.section_id],
                duplicate_of=duplicates.get(section.section_id),
            )
        )
        log(f"labelled {section.section_id} ({section.name}, {section.group}): {len(cells)} cells, "
            f"{counts[section.section_id].differing_cells} differ between the label rules")

    rules = LabelRuleSet(
        dataset_id=DATASET_ID,
        rules=rule_specs(),
        default_label_rule_id=FULL_PANEL_RULE,
        gene_scales={g: gene_scales[g] for g in sorted(gene_scales)},
        gene_scale_sections=CONTROL_SECTION_IDS,
        sections=counts,
        notes=[
            "Labels are assigned once from default-condition counts and frozen for every assignment condition.",
            "Gene scales pool every (section, cell) pair of the control sections that expresses the gene; the spike "
            "grouped by cell id alone, which merges cells whose ids repeat across sections.",
            "Cells with no validated molecules are labelled 'Low quality' and stay in every denominator.",
        ],
        citation=CITATION,
    )
    manifest = DatasetManifest(
        dataset_id=DATASET_ID,
        title="GSE286184: Xenium in situ profiling of human glomerular disease",
        description=(
            "22 GEO Xenium samples of human kidney (Control 3, DKD 6, IgAN 4, MCD 4, MN 5; two IgAN samples hold identical content, "
            "see sections[].duplicate_of) with a 50-gene panel; "
            "molecule tables carry cell_id, overlaps_nucleus and nucleus_distance. No boundaries, images or labels."
        ),
        synthetic=False,
        source_urls=[SERIES_URL, PAPER_URL] + [s.url(k) for s in SECTIONS for k in RAW_KINDS],
        download_date=_download_date(paths.raw_dir),
        coordinate_units="micrometre",
        panel=sorted(panel),
        sections=infos,
        files=[raw_files[s.section_id][k] for s in SECTIONS for k in RAW_KINDS],
        donor_caveat=DONOR_CAVEAT,
        filters=DatasetFilters(
            min_qv=MIN_QV,
            panel_genes_only=True,
            description=(
                f"Molecules need qv >= {MIN_QV:g} and a panel gene (control probes and codewords are removed). "
                "Malformed and duplicate records are removed and counted; molecules assigned to a cell missing from "
                "the cells table are kept as unassigned and counted. Per-section counts are in sections[].validation."
            ),
        ),
        label_rule_ids=list(LABEL_RULES),
        citation=CITATION,
    )
    out = paths.artifacts_dir
    out.mkdir(parents=True, exist_ok=True)
    _write_json(out / "manifest.json", manifest.model_dump(mode="json"))
    _write_json(out / "capability_report.json", capability_report(duplicates).model_dump(mode="json"))
    _write_json(out / "label_rules.json", rules.model_dump(mode="json"))
    log(f"wrote {out}/manifest.json, capability_report.json and label_rules.json")


def _validated(
    section: Section, paths: Paths, raw_files: dict[str, FileChecksum], panel: list[str], log: Callable[[str], None]
) -> tuple[SectionValidation, str]:
    """Validate one section, or reuse its validated tables when the raw files and ingest version are unchanged.
    Also returns the sha256 of the decompressed molecule and cell files, which finds duplicated sections even when
    their gzip wrappers differ."""
    directory = paths.processed(section)
    stamp = {"ingest_version": INGEST_VERSION, "raw_sha256": {k: f.sha256 for k, f in raw_files.items()}}
    stamp_path = directory / "stamp.json"
    if stamp_path.is_file() and json.loads(stamp_path.read_text()) == stamp:
        content = json.loads((directory / "content.json").read_text())["sha256"]
        return SectionValidation.model_validate_json((directory / "validation.json").read_text()), content
    raw = paths.raw_dir / section.section_id
    with gzip.open(raw / section.file_name("transcripts.parquet.gz")) as handle:
        transcript_bytes = handle.read()
    with gzip.open(raw / section.file_name("cells.csv.gz")) as handle:
        cell_bytes = handle.read()
    content = hashlib.sha256(hashlib.sha256(transcript_bytes).digest() + hashlib.sha256(cell_bytes).digest()).hexdigest()
    transcripts = pd.read_parquet(io.BytesIO(transcript_bytes))
    cells = pd.read_csv(io.BytesIO(cell_bytes))
    validated = validate_section(transcripts, cells, panel)
    directory.mkdir(parents=True, exist_ok=True)
    stamp_path.unlink(missing_ok=True)
    _write_parquet(validated.molecules, directory / "molecules.parquet")
    _write_parquet(validated.cells, directory / "cells.validated.parquet")
    (directory / "validation.json").write_text(validated.validation.model_dump_json(indent=1), encoding="utf-8")
    (directory / "content.json").write_text(json.dumps({"sha256": content}), encoding="utf-8")
    stamp_path.write_text(json.dumps(stamp, indent=1, sort_keys=True), encoding="utf-8")
    v = validated.validation
    log(f"validated {section.section_id} ({section.name}): {v.molecules_kept} of {v.molecules_read} molecules kept, "
        f"{v.cells_kept} cells, {v.malformed_molecules} malformed, {v.unmatched_molecules} unmatched")
    return v, content


def _duplicates(contents: dict[str, str]) -> dict[str, str]:
    """Each section whose raw content repeats an earlier section's, mapped to that earlier section."""
    first: dict[str, str] = {}
    duplicates = {}
    for section_id, content in contents.items():
        if content in first:
            duplicates[section_id] = first[content]
        else:
            first[content] = section_id
    return duplicates


def _panel(features_path: Path) -> list[str]:
    features = pd.read_csv(features_path, sep="\t", header=None)
    return sorted(features.loc[features[2] == "Gene Expression", 1].astype(str))


def label_column(rule_id: str) -> str:
    """The processed cells table's column holding labels under a rule."""
    return f"label:{rule_id}"


def _read_molecules(directory: Path, columns: list[str] | None = None) -> pd.DataFrame:
    return pd.read_parquet(directory / "molecules.parquet", columns=columns)


def _write_parquet(frame: pd.DataFrame, path: Path) -> None:
    partial = path.with_name(path.name + ".part")
    frame.to_parquet(partial, index=False)
    partial.replace(path)


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=1, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def _checksum(path: Path, root: Path) -> FileChecksum:
    if not path.is_file():
        raise FileNotFoundError(f"missing raw file {path}; run `spatialscout ingest` without --no-download")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return FileChecksum(path=path.relative_to(root).as_posix(), sha256=digest.hexdigest(), bytes=path.stat().st_size)


def _download_date(raw_dir: Path) -> str:
    """The UTC date the newest raw file was written: stable across reruns until a file is re-downloaded."""
    newest = max((raw_dir / s.section_id / s.file_name(k)).stat().st_mtime for s in SECTIONS for k in RAW_KINDS)
    return datetime.fromtimestamp(newest, UTC).date().isoformat()
