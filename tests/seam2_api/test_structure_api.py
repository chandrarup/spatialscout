"""Seam 2: SAM 3.1 outlines over HTTP, with outbound network blocked.

`POST /api/sections/{id}/sam-outline` takes a box the researcher drew, in section µm, and sends it to SAM 3.1 as a
box prompt on the gene-agnostic nucleus image of a crop around it. The stored response for the box below, on the
synthetic section SYN-01, was recorded live by `scripts/record_sam_box.py`. SYN-01's glomerulus is drawn by
construction as a circle of radius 33 µm centred at (60, 75) (`scripts/build_synthetic_section.py`); the box
encloses it, so any outline returned must lie inside the crop and the box's neighbourhood. Expected values come
from that construction, not from the finder's code.
"""

from spatialscout.contracts import StructureRun

BOX = {"section_id": "SYN-01", "x0": 25.0, "y0": 40.0, "x1": 95.0, "y1": 110.0}


def test_a_drawn_box_is_outlined_from_its_stored_sam_response_with_no_network(client):
    response = client.post("/api/sections/SYN-01/sam-outline", json=BOX)

    assert response.status_code == 200, response.text
    run = StructureRun.model_validate(response.json())
    assert (run.run_mode, run.images_sent, run.model, run.badge) == ("cached_tool_rerun", 1, "sam-3.1", "SAM 3.1 proposal (exploratory)")
    assert run.estimated_cost_usd == 0.0025
    (proposal,) = run.proposals
    assert proposal.seed.origin == "user_box" and proposal.seed.box.model_dump() == BOX
    assert proposal.status == "outlined"  # as recorded
    shapes = [m.shape for m in proposal.comparisons]
    assert shapes[0] == "seed_box" and "convex_hull" not in shapes  # a drawn box has no NPHS1 clusters
    (crop,) = run.crops
    assert crop.x0 <= BOX["x0"] and crop.x1 >= BOX["x1"] and crop.y0 <= BOX["y0"] and crop.y1 >= BOX["y1"]
    for structure in run.structures:
        assert structure.source == "sam-3.1" and structure.run_id == run.run_id and structure.mask_version == run.mask_version
        for x, y in structure.outline:
            assert crop.x0 <= x <= crop.x1 and crop.y0 <= y <= crop.y1


def test_a_box_without_a_stored_response_misses_with_a_clear_message(client):
    response = client.post("/api/sections/SYN-01/sam-outline", json={**BOX, "x1": 96.0})

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "replay_miss"


def test_a_box_on_another_section_or_too_large_is_refused_before_any_model_call(client):
    elsewhere = client.post("/api/sections/SYN-01/sam-outline", json={**BOX, "section_id": "OTHER"})
    huge = client.post("/api/sections/SYN-01/sam-outline", json={**BOX, "x1": 2000.0})
    unknown = client.post("/api/sections/NOPE/sam-outline", json={**BOX, "section_id": "NOPE"})

    assert [elsewhere.status_code, huge.status_code, unknown.status_code] == [400, 400, 404]


def test_a_live_box_prompt_needs_the_passcode(client):
    response = client.post("/api/sections/SYN-01/sam-outline?run_mode=live", json=BOX)

    assert response.status_code == 403
