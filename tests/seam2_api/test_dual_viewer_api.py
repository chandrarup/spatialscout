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
