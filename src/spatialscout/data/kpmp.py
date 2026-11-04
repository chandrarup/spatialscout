"""KPMP CODEX: two participants' multiplexed antibody images (ticket 02c), the real-microscopy layer of revision 3.

    uv run spatialscout kpmp      # or `make kpmp`: needs the raw KPMP downloads in SPATIALSCOUT_KPMP_DIR

Raw files (open access, from the KPMP repository) stay in `data/kpmp/` and are never committed. The build writes:

- the full per-cell table of each participant to `data/processed/KPMP/<participant>/cells.parquet` (git-ignored)
- to `artifacts/KPMP/`: the frozen thresholds, each participant's audit table (the columns the protein audit
  reads) and bordering pairs, the whole-image protein audit results, and browser tiles of the demo channels

GSE286184 data is never drawn on these images: they are different people and a different assay (protein).
"""

import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import tifffile
from PIL import Image

from ..contracts import (
    KpmpChannel,
    KpmpManifest,
    KpmpParticipant,
    KpmpResultEntry,
    KpmpTile,
    ProteinThreshold,
    Region,
)
from ..engine.protein import (
    DATASET,
    MEASUREMENT_CONDITIONS,
    THRESHOLD_RULE,
    adjacent_pairs,
    cell_means,
    channel_index_by_marker,
    measure_cells,
    otsu_threshold,
    protein_audit,
)


@dataclass(frozen=True)
class Participant:
    participant_id: str
    panel_id: str
    role: str
    folder: str


HEALTHY_REFERENCE = Participant("164-17", "23-0159", "healthy reference", "participent_164-17")  # KPMP's folder spelling
PARTICIPANTS = (HEALTHY_REFERENCE, Participant("31-10013", "23-0118", "diseased", "participant_31-10013"))

MEASURED_MARKERS = ("DAPI", "Podocalyxin", "LRP2", "UMOD", "CD20", "CD3", "CD8", "CD45", "aSMA", "CD31")
AUDIT_MARKERS = ("Podocalyxin", "LRP2", "UMOD", "CD20")
RESULTS = (("Podocalyxin", "LRP2"), ("CD20", "UMOD"))
DISPLAY = (
    ("nuclei", "DAPI", "DAPI", "Nuclear stain."),
    ("podocalyxin", "Podocalyxin", "Podocalyxin", "Podocytes and endothelium: glomeruli."),
    ("lrp2", "LRP2", "LRP2", "Megalin: proximal-tubule brush border."),
    ("umod", "UMOD", "UMOD", "Uromodulin: thick ascending limb."),
    ("cd20", "CD20", "CD20", "B cells."),
    ("cd3", "CD3", "CD3", "T cells."),
    ("asma", "aSMA", "aSMA", "Smooth muscle actin: vessels and myofibroblasts."),
)
DOWNSAMPLE = 2
STRIP_ROWS = 2048
DISPLAY_PERCENTILE = 99.7
DISPLAY_RULE = (
    f"Display only: {DOWNSAMPLE} x {DOWNSAMPLE} block means, scaled linearly so 0 is black and the "
    f"{DISPLAY_PERCENTILE}th percentile of in-cell pixels is full brightness. Measurements use the raw pixels."
)
CLINICAL_NOTE = "Clinical metadata not downloaded: no clinical value is shown."


@dataclass(frozen=True)
class RawFiles:
    stack: Path
    channel_key: Path
    mask: Path


def raw_files(kpmp_dir: Path, participant: Participant) -> RawFiles:
    folder = kpmp_dir / participant.folder
    stacks = sorted(folder.glob("*_image_collection*/*DAPIcomposite.tif"))
    keys = sorted(folder.glob("*_image_collection*/*ChannelKey.csv"))
    masks = sorted(folder.glob("*_segmentation_data/*SegmentationMask.tif"))
    if not (stacks and keys and masks):
        raise FileNotFoundError(f"{folder}: needs an unzipped image collection (DAPIcomposite.tif, ChannelKey.csv) and segmentation data")
    return RawFiles(stacks[0], keys[0], masks[0])


def pixel_size_um(stack: Path) -> float:
    """From the TIFF's XResolution, in pixels per micron (ImageJ, unit=micron)."""
    with tifffile.TiffFile(stack) as tif:
        numerator, denominator = tif.pages[0].tags["XResolution"].value
    return denominator / numerator


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def build(kpmp_dir: Path, processed_dir: Path, artifacts_dir: Path, log=print) -> KpmpManifest:
    """Measure both participants, freeze thresholds on the healthy reference, compute the whole-image results and
    write the tiles. Idempotent: the same raw files give the same artifacts."""
    out = artifacts_dir / "KPMP"
    out.mkdir(parents=True, exist_ok=True)
    opened = {p.participant_id: _open(kpmp_dir, p) for p in PARTICIPANTS}

    reference = opened[HEALTHY_REFERENCE.participant_id]
    inside = reference["labels"] > 0
    nucleus = ProteinThreshold(
        marker="DAPI", value=otsu_threshold(reference["stack"][reference["index"]["DAPI"]][inside]),
        rule="Otsu's threshold on the healthy reference's DAPI pixels inside cells (256 bins of width 1); the nucleus region is a cell's pixels at or above it.",
        source_participant_id=HEALTHY_REFERENCE.participant_id,
    )
    del inside
    log(f"nucleus threshold (DAPI) {nucleus.value:g} from {HEALTHY_REFERENCE.participant_id}")

    tables: dict[str, pd.DataFrame] = {}
    pairs: dict[str, np.ndarray] = {}
    for participant in PARTICIPANTS:
        o = opened[participant.participant_id]
        stack, index = o["stack"], o["index"]
        channels = {m: (lambda m=m: np.asarray(stack[index[m]])) for m in MEASURED_MARKERS}
        table = measure_cells(o["labels"], channels, dapi=lambda: np.asarray(stack[index["DAPI"]]),
                              nucleus_threshold=nucleus.value, pixel_size_um=o["pixel_size_um"])
        full = processed_dir / participant.participant_id / "cells.parquet"
        full.parent.mkdir(parents=True, exist_ok=True)
        table.to_parquet(full, index=False)
        tables[participant.participant_id] = table
        pairs[participant.participant_id] = adjacent_pairs(o["labels"])
        log(f"{participant.participant_id}: {len(table):,} cells, {len(pairs[participant.participant_id]):,} bordering pairs")

    ref_table = tables[HEALTHY_REFERENCE.participant_id]
    thresholds = [
        ProteinThreshold(marker=m, value=otsu_threshold(cell_means(ref_table, m, "whole_cell").to_numpy()),
                         rule=THRESHOLD_RULE, source_participant_id=HEALTHY_REFERENCE.participant_id)
        for m in AUDIT_MARKERS
    ]
    (out / "thresholds.json").write_text(
        json.dumps({"nucleus": nucleus.model_dump(mode="json"), "markers": [t.model_dump(mode="json") for t in thresholds]}, indent=1) + "\n",
        encoding="utf-8",
    )

    participants, entries = [], []
    for participant in PARTICIPANTS:
        pid = participant.participant_id
        o = opened[pid]
        audit_table = audit_columns(tables[pid])
        folder = out / pid
        folder.mkdir(parents=True, exist_ok=True)
        table_path = folder / "cells.parquet"
        audit_table.to_parquet(table_path, index=False)
        pd.DataFrame(pairs[pid], columns=["a", "b"]).to_parquet(folder / "pairs.parquet", index=False)
        checksum = _sha256(table_path)
        for population_marker, marker in RESULTS:
            result = protein_audit(audit_table, pairs[pid], participant_id=pid, role=participant.role,
                                   population_marker=population_marker, marker=marker, thresholds=thresholds,
                                   cell_table_checksum=checksum)
            path = folder / f"audit_{population_marker.lower()}_{marker.lower()}.json"
            path.write_text(result.model_dump_json(indent=1) + "\n", encoding="utf-8")
            entries.append(KpmpResultEntry(participant_id=pid, population_marker=population_marker, marker=marker,
                                           label=result.label, path=_rel(path, artifacts_dir)))
            log(f"{pid}: {result.population} / {marker}: {result.label.value} ({result.label_reason})")
        height, width = o["labels"].shape
        ps = o["pixel_size_um"]
        coverage = float((o["labels"] > 0).mean())
        median_area = float(audit_table["area_um2"].median())
        participants.append(KpmpParticipant(
            participant_id=pid,
            panel_id=participant.panel_id,
            role=participant.role,
            title=f"KPMP participant {pid} ({participant.role}) · CODEX panel {participant.panel_id}",
            extent=Region(section_id=pid, x0=0.0, y0=0.0, x1=width * ps, y1=height * ps),
            pixel_size_um=ps,
            cells=len(audit_table),
            mask_coverage=coverage,
            median_cell_area_um2=median_area,
            mask_note=(
                f"KPMP's segmentation labels cover {coverage:.1%} of the image with a median area of {median_area:.0f} µm², "
                "about nucleus-sized, so 'whole cell' means the whole mask label: the nucleus and a thin rim, not the cytoplasm."
            ),
            channels=write_tiles(o, pid, out, artifacts_dir, log),
            clinical={},
            clinical_note=CLINICAL_NOTE,
            source_files=[o["files"].stack.name, o["files"].channel_key.name, o["files"].mask.name],
        ))

    manifest = KpmpManifest(dataset_id=DATASET, participants=participants, nucleus_threshold=nucleus,
                            thresholds=thresholds, results=entries, display_rule=DISPLAY_RULE)
    (out / "manifest.json").write_text(manifest.model_dump_json(indent=1) + "\n", encoding="utf-8")
    return manifest


def _open(kpmp_dir: Path, participant: Participant) -> dict:
    files = raw_files(kpmp_dir, participant)
    index = channel_index_by_marker(files.channel_key.read_text(encoding="utf-8-sig"))
    missing = [m for m in (*MEASURED_MARKERS, *(d[1] for d in DISPLAY)) if m not in index]
    if missing:
        raise ValueError(f"{participant.participant_id}: panel {participant.panel_id} has no {', '.join(missing)} channel")
    labels = tifffile.imread(files.mask)
    if not np.array_equal(labels, np.round(labels)):
        raise ValueError(f"{files.mask.name}: labels are not whole numbers")
    return {"files": files, "index": index, "stack": tifffile.memmap(files.stack), "labels": labels.astype(np.int32),
            "pixel_size_um": pixel_size_um(files.stack)}


def audit_columns(table: pd.DataFrame) -> pd.DataFrame:
    """The columns the protein audit reads, for the audit markers only: small enough to commit and ship."""
    keep = ["cell_id", "x_um", "y_um", "area_um2", *(f"pixels__{c}" for c in MEASUREMENT_CONDITIONS)]
    for marker in AUDIT_MARKERS:
        keep += [f"{marker}__{c}__sum" for c in MEASUREMENT_CONDITIONS] + [f"{marker}__whole_cell__sumsq"]
    return table[keep].copy()


def write_tiles(opened: dict, pid: str, out: Path, artifacts_dir: Path, log) -> list[KpmpChannel]:
    stack, index, labels, ps = opened["stack"], opened["index"], opened["labels"], opened["pixel_size_um"]
    inside = labels > 0
    channels = []
    for channel_id, marker, label, description in DISPLAY:
        image = np.asarray(stack[index[marker]])
        top = float(np.percentile(image[inside], DISPLAY_PERCENTILE)) or 1.0
        height, width = (image.shape[0] // DOWNSAMPLE) * DOWNSAMPLE, (image.shape[1] // DOWNSAMPLE) * DOWNSAMPLE
        small = image[:height, :width].reshape(height // DOWNSAMPLE, DOWNSAMPLE, width // DOWNSAMPLE, DOWNSAMPLE).mean(axis=(1, 3))
        scaled = np.clip(small / top * 255.0, 0, 255).astype(np.uint8)
        tiles = []
        folder = out / "tiles" / pid / channel_id
        folder.mkdir(parents=True, exist_ok=True)
        step = ps * DOWNSAMPLE
        for n, start in enumerate(range(0, scaled.shape[0], STRIP_ROWS)):
            strip = scaled[start:start + STRIP_ROWS]
            path = folder / f"{n:02d}.webp"
            buffer = io.BytesIO()
            Image.fromarray(strip, mode="L").save(buffer, format="WEBP", quality=82, method=4)
            path.write_bytes(buffer.getvalue())
            tiles.append(KpmpTile(path=_rel(path, artifacts_dir), bounds=Region(
                section_id=pid, x0=0.0, y0=start * step, x1=strip.shape[1] * step, y1=(start + strip.shape[0]) * step)))
        channels.append(KpmpChannel(channel_id=channel_id, marker=marker, label=label, description=description,
                                    display_max=top, tiles=tiles))
        log(f"{pid}: tiles for {marker} (white at {top:g})")
    return channels
