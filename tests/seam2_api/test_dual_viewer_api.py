"""Seam 2: what the dual-section viewer asks of the API, with outbound network blocked.

SYN-01 (`scripts/build_synthetic_section.py`): 12 cells, each with a nucleus. Assigned molecules: 3 podocytes with
20 NPHS1 each, except C03, whose expansion zone holds 1 NPHS1 and 4 LRP2 (56 NPHS1, 4 LRP2); 4 PT cells with 11
LRP2 and 9 CUBN each (80); 2 TAL cells with 20 UMOD each (40); 1 T cell with 20 CD3D. The 60 unassigned molecules
cycle through the 7 panel genes in sorted order (CD3D, CUBN, LRP2, NPHS1, PDGFRB, PECAM1, UMOD), so CD3D, CUBN,
LRP2 and NPHS1 get 9 each and the other three get 8. No CD8A, MS4A1 or POSTN molecule exists.
"""


def test_a_sections_rendered_channels_count_every_molecule_of_their_genes(client):
    response = client.get("/api/sections/SYN-01/channels")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["provenance"] == "rendered from molecules"
    counts = {c["channel_id"]: c["count"] for c in body["channels"]}
    assert counts == {"nuclei": 12, "nphs1": 65, "lrp2_cubn": 102, "umod": 48, "lymphocyte": 29, "postn": 0}
    channels = {c["channel_id"]: c for c in body["channels"]}
    assert channels["lymphocyte"]["available"] and channels["lymphocyte"]["missing_genes"] == ["CD8A", "MS4A1"]
    assert not channels["postn"]["available"]


def test_channels_of_an_unknown_section_are_not_found(client):
    assert client.get("/api/sections/NOPE/channels").status_code == 404


def test_the_recorded_boxes_of_a_section_each_replay_a_sam_outline_with_no_model_call(client):
    response = client.get("/api/sections/SYN-01/sam-boxes")

    assert response.status_code == 200, response.text
    boxes = response.json()["boxes"]
    assert {"section_id": "SYN-01", "x0": 25.0, "y0": 40.0, "x1": 95.0, "y1": 110.0} in boxes
    for box in boxes:
        outline = client.post("/api/sections/SYN-01/sam-outline", json=box)
        assert outline.status_code == 200, outline.text
        assert outline.json()["badge"] == "SAM 3.1 proposal (exploratory)"


RECORDED_QUESTION = "Does podocyte LRP2 in the synthetic section survive nucleus-only assignment?"
GLOMERULUS_BOX = {"section_id": "SYN-01", "x0": 25.0, "y0": 40.0, "x1": 95.0, "y1": 110.0}
TUBULE_BOX = {"section_id": "SYN-01", "x0": 100.0, "y0": 20.0, "x1": 160.0, "y1": 120.0}


def test_the_region_pair_drawn_in_the_viewer_reaches_the_investigation_as_context(client):
    response = client.post("/api/investigations", json={"question": RECORDED_QUESTION, "regions": [GLOMERULUS_BOX, TUBULE_BOX]})

    assert response.status_code == 201, response.text
    assert response.json()["regions"] == [GLOMERULUS_BOX, TUBULE_BOX]
    again = client.get(f"/api/investigations/{response.json()['investigation_id']}").json()
    assert again["regions"] == [GLOMERULUS_BOX, TUBULE_BOX]


def test_an_investigation_started_without_regions_has_none(client):
    response = client.post("/api/investigations", json={"question": RECORDED_QUESTION})

    assert response.status_code == 201 and response.json()["regions"] == []


def test_a_region_off_the_investigated_dataset_or_with_no_area_is_refused_and_nothing_is_created(client):
    elsewhere = client.post("/api/investigations", json={"question": RECORDED_QUESTION, "regions": [{**GLOMERULUS_BOX, "section_id": "GSM-OTHER"}]})
    flat = client.post("/api/investigations", json={"question": RECORDED_QUESTION, "regions": [{**GLOMERULUS_BOX, "x1": 25.0}]})

    assert elsewhere.status_code == 422, elsewhere.text
    assert flat.status_code == 422, flat.text


def test_a_section_with_no_recorded_box_lists_none(client):
    response = client.get("/api/sections/NOPE/sam-boxes")

    assert response.status_code == 200 and response.json() == {"section_id": "NOPE", "boxes": []}
