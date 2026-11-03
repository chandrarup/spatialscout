"""HTTP routes for the assignment audit: the committed audit results, their figures and controls, and the live
gate status of a box the researcher drags."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse

from ..contracts import AuditIndex, AuditResult, GateStatus, LabelSensitivityCheck, RandomThinningControl, Region
from ..data import DatasetStore, SectionNotIngested, UnknownLabelRule, UnknownSection
from ..engine import gate_status
from ..settings import Settings

router = APIRouter()


def _audit_dir(request: Request, dataset_id: str) -> Path:
    settings: Settings = request.app.state.settings
    if settings.artifacts_dir is None:
        raise HTTPException(status_code=404, detail="no artifacts directory is configured")
    return settings.artifacts_dir / dataset_id / "audit"


@lru_cache(maxsize=8)
def _read_index(path: Path, mtime: float) -> AuditIndex:
    return AuditIndex.model_validate_json(path.read_text(encoding="utf-8"))


def _index(request: Request, dataset_id: str) -> tuple[Path, AuditIndex]:
    directory = _audit_dir(request, dataset_id)
    path = directory / "index.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"no committed audit results for {dataset_id}; run `make audit`")
    return directory.parent, _read_index(path, path.stat().st_mtime)


@router.get("/datasets/{dataset_id}/audit-results")
async def audit_results(dataset_id: str, request: Request) -> AuditIndex:
    """The committed audit results of a dataset, each with its label, figure and controls."""
    return _index(request, dataset_id)[1]


def _entry_file(request: Request, dataset_id: str, finding_id: str, field: str) -> Path:
    root, index = _index(request, dataset_id)
    entry = next((e for e in index.entries if e.finding_id == finding_id), None)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"no audit result {finding_id} in {dataset_id}")
    if field == "figure":
        if entry.figure is None:
            raise HTTPException(status_code=404, detail=f"audit result {finding_id} has no composite figure")
        return root / entry.figure.path
    relative = getattr(entry, field)
    if relative is None:
        raise HTTPException(status_code=404, detail=f"audit result {finding_id} has no {field.removesuffix('_path')}")
    return root / relative


@router.get("/datasets/{dataset_id}/audit-results/{finding_id}")
async def audit_result(dataset_id: str, finding_id: str, request: Request) -> AuditResult:
    return AuditResult.model_validate(json.loads(_entry_file(request, dataset_id, finding_id, "finding_path").read_text()))


@router.get("/datasets/{dataset_id}/audit-results/{finding_id}/figure.png")
async def audit_figure(dataset_id: str, finding_id: str, request: Request) -> FileResponse:
    return FileResponse(_entry_file(request, dataset_id, finding_id, "figure"), media_type="image/png")


@router.get("/datasets/{dataset_id}/audit-results/{finding_id}/random-thinning-control")
async def random_thinning(dataset_id: str, finding_id: str, request: Request) -> RandomThinningControl:
    path = _entry_file(request, dataset_id, finding_id, "random_thinning_control_path")
    return RandomThinningControl.model_validate_json(path.read_text())


@router.get("/datasets/{dataset_id}/audit-results/{finding_id}/label-sensitivity-check")
async def label_sensitivity(dataset_id: str, finding_id: str, request: Request) -> LabelSensitivityCheck:
    path = _entry_file(request, dataset_id, finding_id, "label_sensitivity_control_path")
    return LabelSensitivityCheck.model_validate_json(path.read_text())


@router.get("/sections/{section_id}/gate-status")
def section_gate_status(
    section_id: str,
    request: Request,
    cell_type: str,
    genes: Annotated[list[str], Query(min_length=1)],
    label_rule_id: str | None = None,
    x0: float | None = None,
    y0: float | None = None,
    x1: float | None = None,
    y1: float | None = None,
) -> GateStatus:
    """Cells of the population and their molecules of `genes` inside the box, against the frozen gates. Without
    a box, the whole section. A plain `def`, so a first load of a large section runs off the event loop."""
    store: DatasetStore = request.app.state.store
    try:
        section = store.load_section(section_id, label_rule_id)
    except UnknownSection:
        raise HTTPException(status_code=404, detail=f"no section {section_id}") from None
    except UnknownLabelRule:
        raise HTTPException(status_code=404, detail=f"no label rule {label_rule_id} for section {section_id}") from None
    except SectionNotIngested as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    box = [x0, y0, x1, y1]
    if any(v is None for v in box) and any(v is not None for v in box):
        raise HTTPException(status_code=422, detail="a box needs all of x0, y0, x1 and y1")
    roi = None
    if x0 is not None:
        roi = Region(section_id=section_id, x0=min(x0, x1), y0=min(y0, y1), x1=max(x0, x1), y1=max(y0, y1))  # type: ignore[type-var]
    return gate_status(section, roi, cell_type, genes)
