"""SAM 3.1 outlines (exploratory, ADR-0006): a section's committed structure-finder run, and a box the researcher
drew sent to SAM 3.1 as its box prompt (revision 3), and the boxes whose response is stored, which the dual-section
viewer offers as recorded boxes."""

import json
from typing import Annotated, Literal

from fastapi import APIRouter, Header, HTTPException, Request

from ..agent import utc_now
from ..contracts import RecordedBoxes, Recording, Region, StructureRun
from ..data import DatasetStore, SectionNotIngested, UnknownSection
from ..engine.structure_finder import outline_box, recording_path
from ..gateway import GatewayError, LiveRunRefused, LiveSource, ModelGateway, ProviderError, ReplaySource, StoredResponseMissing
from ..gateway.gate import LiveGate
from ..settings import Settings

router = APIRouter()

USER_BOXES = "user_boxes"  # fixtures/sam/user_boxes.json: stored responses for drawn boxes
USER_BOX_PROMPTS = "user_box_prompts"  # fixtures/sam/user_box_prompts.json: the boxes those responses answer


def recorded_boxes(fixtures_dir) -> list[Region]:
    """Every box whose SAM 3.1 response is stored, from the list `scripts/record_sam_box.py` records."""
    path = recording_path(fixtures_dir, USER_BOX_PROMPTS)
    if not path.is_file():
        return []
    return [Region.model_validate(box) for box in json.loads(path.read_text(encoding="utf-8"))["boxes"]]


def _problem(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


@router.get("/sections/{section_id}/structures")
async def structure_run(section_id: str, request: Request) -> StructureRun:
    """The section's committed SAM 3.1 run: every seed's proposal (outlined, fragmented, empty or rejected), its
    comparison with the seed box and the convex-hull baseline, and the images sent with their cost."""
    store: DatasetStore = request.app.state.store
    run = store.structure_run(section_id)
    if run is None:
        raise _problem(404, "no_structure_run", f"Section {section_id} has no SAM 3.1 outlines.")
    return run


@router.get("/sections/{section_id}/sam-boxes")
async def sam_boxes(section_id: str, request: Request) -> RecordedBoxes:
    """Boxes on the section whose SAM 3.1 response is stored, so a cached tool rerun can outline them; any other
    box needs a live run."""
    settings: Settings = request.app.state.settings
    return RecordedBoxes(section_id=section_id, boxes=[b for b in recorded_boxes(settings.fixtures_dir) if b.section_id == section_id])


@router.post("/sections/{section_id}/sam-outline")
async def sam_outline(
    section_id: str,
    box: Region,
    request: Request,
    run_mode: Literal["cached_tool_rerun", "live"] = "cached_tool_rerun",
    x_live_passcode: Annotated[str | None, Header()] = None,
) -> StructureRun:
    """Outline what lies in a box drawn on the section (µm) with SAM 3.1, prompted with that box on the gene-agnostic
    nucleus image of a crop around it. A cached tool rerun serves a stored response and never calls a model; a live
    call (one image, about $0.0025) needs the passcode in `X-Live-Passcode` and budget left today. The outline is a
    proposal, badged exploratory, and enters no evidence label."""
    store: DatasetStore = request.app.state.store
    settings: Settings = request.app.state.settings
    if box.section_id != section_id:
        raise _problem(400, "invalid_box", f"The box is on section {box.section_id}, not {section_id}.")
    try:
        section = store.load_section(section_id)
    except UnknownSection:
        raise _problem(404, "unknown_section", f"No section {section_id}.") from None
    except SectionNotIngested as error:
        raise _problem(409, "section_not_ingested", str(error)) from None

    if run_mode == "live":
        live_gate: LiveGate = request.app.state.live_gate
        try:
            source = LiveSource(live_gate.admit(x_live_passcode))
        except LiveRunRefused as refused:
            raise _problem(403, refused.code, str(refused)) from None
    else:
        path = recording_path(settings.fixtures_dir, USER_BOXES)
        if not path.is_file():
            raise _problem(404, StoredResponseMissing.code, "This server has no stored SAM 3.1 responses for drawn boxes.")
        source = ReplaySource(Recording.model_validate_json(path.read_text(encoding="utf-8")))

    gateway = ModelGateway(source, utc_now, run_mode=run_mode)
    try:
        return await outline_box(section, box, gateway, run_mode)
    except ValueError as error:
        raise _problem(400, "invalid_box", str(error)) from None
    except StoredResponseMissing:
        raise _problem(
            404, StoredResponseMissing.code,
            "This server replays stored responses and has none for this box. Draw one of the recorded boxes, or run live.",
        ) from None
    except ProviderError as error:
        raise _problem(502, error.code, f"SAM 3.1 failed: {error}") from None
    except GatewayError as error:
        raise _problem(502, error.code, f"SAM 3.1 call failed: {error}") from None
