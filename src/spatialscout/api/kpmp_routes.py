"""KPMP CODEX (ticket 02c): the manifest of the two participants, their display tiles, and the protein audit of a
region drawn on either image, computed on request from the committed audit table."""

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from ..contracts import KpmpCellMap, KpmpManifest, ProteinAuditResult, Region
from ..data.kpmp import AUDIT_MARKERS, RESULTS
from ..engine.protein import cell_means, positive, protein_audit
from ..settings import Settings

router = APIRouter()


def _problem(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def _root(request: Request) -> Path:
    settings: Settings = request.app.state.settings
    assert settings.artifacts_dir is not None
    return settings.artifacts_dir


@lru_cache(maxsize=4)
def _manifest(path: Path, mtime: float) -> KpmpManifest:
    return KpmpManifest.model_validate_json(path.read_text(encoding="utf-8"))


def load_manifest(artifacts_dir: Path) -> KpmpManifest:
    path = artifacts_dir / "KPMP" / "manifest.json"
    if not path.is_file():
        raise _problem(404, "kpmp_not_built", "This server has no KPMP CODEX artifacts. Run `make kpmp`.")
    return _manifest(path, path.stat().st_mtime)


@lru_cache(maxsize=4)
def _tables(folder: Path, mtime: float) -> tuple[pd.DataFrame, np.ndarray, str]:
    import hashlib

    table_path = folder / "cells.parquet"
    checksum = hashlib.sha256(table_path.read_bytes()).hexdigest()
    pairs = pd.read_parquet(folder / "pairs.parquet")[["a", "b"]].to_numpy()
    return pd.read_parquet(table_path), pairs, checksum


@router.get("/kpmp")
async def kpmp_manifest(request: Request) -> KpmpManifest:
    """Both participants: extent, display channels and their tiles, mask statistics, frozen thresholds, and the
    whole-image protein audit results with their labels. Clinical values appear only from downloaded KPMP files."""
    return load_manifest(_root(request))


@router.get("/kpmp/files/{path:path}")
async def kpmp_file(path: str, request: Request) -> FileResponse:
    """A committed KPMP artifact (a tile or a result), by its path under the artifacts directory."""
    root = (_root(request) / "KPMP").resolve()
    target = (_root(request) / path).resolve()
    if root not in target.parents or not target.is_file():
        raise _problem(404, "no_such_file", f"No KPMP artifact at {path}.")
    return FileResponse(target, headers={"Cache-Control": "public, max-age=86400"})


@router.get("/kpmp/{participant_id}/protein-audit")
async def kpmp_protein_audit(
    participant_id: str,
    request: Request,
    population_marker: str,
    marker: str,
    x0: float | None = None,
    y0: float | None = None,
    x1: float | None = None,
    y1: float | None = None,
) -> ProteinAuditResult:
    """The protein audit of one participant over the whole image, or over a box (µm, cells by centroid) when all
    four corners are given, with the frozen thresholds. Descriptive: one participant, in this scope."""
    manifest = load_manifest(_root(request))
    participant = next((p for p in manifest.participants if p.participant_id == participant_id), None)
    if participant is None:
        raise _problem(404, "unknown_participant", f"No KPMP participant {participant_id}.")
    if (population_marker, marker) not in RESULTS:
        raise _problem(400, "unknown_result", f"Results are {', '.join(f'{m} in {p}+ cells' for p, m in RESULTS)}.")
    corners = (x0, y0, x1, y1)
    roi = None
    if any(c is not None for c in corners):
        if any(c is None for c in corners) or x1 <= x0 or y1 <= y0:  # type: ignore[operator]
            raise _problem(400, "invalid_box", "A box needs x0 < x1 and y0 < y1, in micrometres.")
        roi = Region(section_id=participant_id, x0=x0, y0=y0, x1=x1, y1=y1)  # type: ignore[arg-type]
    folder = _root(request) / "KPMP" / participant_id
    table, pairs, checksum = _tables(folder, (folder / "cells.parquet").stat().st_mtime)
    return protein_audit(table, pairs, participant_id=participant_id, role=participant.role,
                         population_marker=population_marker, marker=marker, thresholds=manifest.thresholds,
                         cell_table_checksum=checksum, roi=roi)


CELL_MAP_CONDITION = "whole_cell"


@lru_cache(maxsize=4)
def _cell_map(folder: Path, mtime: float, participant_id: str, thresholds_json: str) -> KpmpCellMap:
    manifest_thresholds = KpmpManifest.model_validate_json(thresholds_json).thresholds
    table = pd.read_parquet(folder / "cells.parquet")
    by_marker = {t.marker: t for t in manifest_thresholds}
    markers = [m for m in AUDIT_MARKERS if m in by_marker]
    mask = np.zeros(len(table), dtype=np.int64)
    for bit, marker in enumerate(markers):
        mask |= positive(table, marker, CELL_MAP_CONDITION, by_marker[marker].value).astype(np.int64) << bit
    keep = mask > 0
    means = np.stack([cell_means(table, m, CELL_MAP_CONDITION).to_numpy() for m in markers], axis=1)[keep]
    return KpmpCellMap(
        participant_id=participant_id,
        condition=CELL_MAP_CONDITION,
        markers=markers,
        thresholds=[by_marker[m] for m in markers],
        total_cells=int(len(table)),
        cell_id=table["cell_id"].to_numpy()[keep].astype(int).tolist(),
        x_um=np.round(table["x_um"].to_numpy()[keep], 1).tolist(),
        y_um=np.round(table["y_um"].to_numpy()[keep], 1).tolist(),
        positive=mask[keep].astype(int).tolist(),
        means=np.round(np.nan_to_num(means), 1).tolist(),
        rule=(
            f"A cell is drawn when its {CELL_MAP_CONDITION.replace('_', ' ')} mean of a marker reaches that marker's frozen "
            "threshold (Otsu on the healthy reference). KPMP's segmentation masks are nucleus-sized, so this marks "
            "marker-positive nuclei, not cell types."
        ),
    )


@router.get("/kpmp/{participant_id}/cells")
async def kpmp_cells(participant_id: str, request: Request) -> KpmpCellMap:
    """The participant's marker-positive cells under the frozen thresholds: centroids, a bitmask over the audit
    markers and each cell's means, computed from the committed audit table."""
    manifest = load_manifest(_root(request))
    if not any(p.participant_id == participant_id for p in manifest.participants):
        raise _problem(404, "unknown_participant", f"No KPMP participant {participant_id}.")
    folder = _root(request) / "KPMP" / participant_id
    thresholds = KpmpManifest.model_validate(manifest).model_dump_json()
    return _cell_map(folder, (folder / "cells.parquet").stat().st_mtime, participant_id, thresholds)
