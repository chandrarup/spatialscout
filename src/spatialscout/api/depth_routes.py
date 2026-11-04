"""HTTP routes for measured molecule depth: which sections have a verified depth sidecar, a box's molecules with z for
the 3D view (sampled to a point budget, with full counts), and a box's descriptive depth profile. Sidecars sit beside
the processed tables (`depth.parquet` and `depth.json`, from `make depth`); a section without one says so."""

import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, Request

from ..contracts import DepthPoints, DepthProfile, DepthProfileRequest, DepthSource, Region
from ..data import DatasetStore, SectionNotIngested, SectionTables, UnknownLabelRule, UnknownSection
from ..engine.depth import DepthJoinError, depth_points, depth_profile
from ..settings import Settings

router = APIRouter()

MAX_POINTS = 60_000


def _dir(request: Request) -> Path | None:
    settings: Settings = request.app.state.settings
    return settings.depth_dir or settings.processed_dir


@lru_cache(maxsize=4)
def _read(parquet: Path, mtime: float, expected_sha256: str) -> pd.DataFrame:
    if hashlib.sha256(parquet.read_bytes()).hexdigest() != expected_sha256:
        raise DepthJoinError(f"{parquet.name} does not match the checksum recorded in depth.json")
    return pd.read_parquet(parquet)


def _source(request: Request, section_id: str) -> tuple[DepthSource, Path]:
    root = _dir(request)
    meta = root / section_id / "depth.json" if root else None
    if meta is None or not meta.is_file():
        verified = ", ".join(available(request)) or "none"
        raise HTTPException(status_code=404, detail=f"no verified depth for section {section_id}; sections with measured depth: {verified}")
    return DepthSource.model_validate_json(meta.read_text()), meta.with_name("depth.parquet")


def available(request: Request) -> list[str]:
    root = _dir(request)
    return sorted(p.parent.name for p in root.glob("*/depth.json")) if root and root.is_dir() else []


def _load(request: Request, section_id: str, label_rule_id: str | None) -> tuple[SectionTables, pd.DataFrame, DepthSource]:
    source, parquet = _source(request, section_id)
    store: DatasetStore = request.app.state.store
    try:
        section = store.load_section(section_id, label_rule_id)
        sidecar = _read(parquet, parquet.stat().st_mtime, source.sidecar_sha256)
    except UnknownSection:
        raise HTTPException(status_code=404, detail=f"no section {section_id}") from None
    except UnknownLabelRule:
        raise HTTPException(status_code=404, detail=f"no label rule {label_rule_id} for section {section_id}") from None
    except SectionNotIngested as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except DepthJoinError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    return section, sidecar, source


@router.get("/depth/sections")
def depth_sections(request: Request) -> list[str]:
    """Sections with a verified measured-depth sidecar."""
    return available(request)


@router.get("/sections/{section_id}/depth")
def section_depth(section_id: str, request: Request) -> DepthSource:
    return _source(request, section_id)[0]


@router.get("/sections/{section_id}/depth/points")
def section_depth_points(
    section_id: str,
    request: Request,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    genes: Annotated[list[str], Query(min_length=1)],
    z0: float | None = None,
    z1: float | None = None,
    budget: int = Query(default=40_000, ge=1, le=MAX_POINTS),
    label_rule_id: str | None = None,
) -> DepthPoints:
    """A box's molecules of `genes` with measured z, for drawing. A plain `def`: a first load runs off the event loop."""
    section, sidecar, _ = _load(request, section_id, label_rule_id)
    region = Region(section_id=section_id, x0=min(x0, x1), y0=min(y0, y1), x1=max(x0, x1), y1=max(y0, y1))
    z_range = (min(z0, z1), max(z0, z1)) if z0 is not None and z1 is not None else None
    try:
        return depth_points(section, sidecar, region, genes, z_range, budget)
    except DepthJoinError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None


@router.post("/sections/{section_id}/depth-profile")
def section_depth_profile(section_id: str, body: DepthProfileRequest, request: Request) -> DepthProfile:
    """Full-data counts of a box by depth interval, gene and assignment condition: new descriptive exploration."""
    if body.region.section_id != section_id:
        raise HTTPException(status_code=422, detail=f"the box is on section {body.region.section_id}, not {section_id}")
    if body.region.x1 <= body.region.x0 or body.region.y1 <= body.region.y0:
        raise HTTPException(status_code=422, detail="the box has no area")
    section, sidecar, source = _load(request, section_id, body.label_rule_id)
    try:
        return depth_profile(section, sidecar, source, body.region, body.genes, body.bin_um, body.cell_type)
    except DepthJoinError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
