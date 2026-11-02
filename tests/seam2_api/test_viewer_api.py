"""Seam 2: what the viewer and the run-mode banner read from the API."""

from .conftest import RECORDED_QUESTION


def test_the_mode_names_the_run_mode_and_offers_the_recorded_question(client):
    mode = client.get("/api/mode").json()

    assert mode["default_run_mode"] == "cached_tool_rerun"
    assert [(r["question"], r["origin"]) for r in mode["recordings"]] == [(RECORDED_QUESTION, "hand_authored")]


def test_the_region_view_ships_the_synthetic_section_as_compact_columns(client):
    view = client.get("/api/sections/SYN-01/region-view").json()

    assert (len(view["molecules"]["x"]), len(view["cells"]["cell_id"]), len(view["structures"])) == (300, 12, 1)
    # 240 assigned molecules count under the default condition; nucleus-only keeps the 180 nuclear ones.
    assert sum(view["molecules"]["included"]["default"]) == 240
    assert sum(view["molecules"]["included"]["nucleus_only"]) == 180


def test_an_unknown_section_is_not_found(client):
    assert client.get("/api/sections/NOPE/region-view").status_code == 404
