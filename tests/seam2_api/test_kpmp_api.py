"""Seam 2: KPMP CODEX (ticket 02c) through the HTTP API, on two tiny participants built on disk by the real
`spatialscout kpmp` build: the manifest, the display tiles, and the protein audit of a drawn box."""

from dataclasses import replace

import numpy as np
import pytest
import tifffile
from fastapi.testclient import TestClient

from spatialscout.api import create_app
from spatialscout.data.kpmp import DISPLAY, MEASURED_MARKERS, PARTICIPANTS, build

from .conftest import make_settings

SIZE, STRIDE = 64, 4  # 16 x 16 cells of 3 x 3 px, one background pixel apart
PX_PER_UM = 2.0


def write_participant(folder, panel_id: str) -> None:
    """Cell n (row-major) is Podocalyxin+ for n < 100, LRP2+ for n < 50, CD20+ for 100 <= n < 160 and UMOD+ for
    130 <= n < 220; DAPI is 200 at each cell's centre pixel."""
    markers = list(dict.fromkeys([*MEASURED_MARKERS, *(d[1] for d in DISPLAY)]))
    labels = np.zeros((SIZE, SIZE), dtype=np.float32)
    stack = np.zeros((len(markers), SIZE, SIZE), dtype=np.uint8)
    plane = {m: i for i, m in enumerate(markers)}
    for n in range(256):
        r, c = (n // 16) * STRIDE, (n % 16) * STRIDE
        labels[r:r + 3, c:c + 3] = n + 1
        stack[plane["DAPI"], r + 1, c + 1] = 200
        for marker, on in (("Podocalyxin", n < 100), ("LRP2", n < 50), ("CD20", 100 <= n < 160), ("UMOD", 130 <= n < 220)):
            if on:
                stack[plane[marker], r:r + 3, c:c + 3] = 120
    (folder / "x_image_collection-v2").mkdir(parents=True)
    (folder / "x_segmentation_data").mkdir()
    key = "Channel,Marker\n" + "".join(f"{i + 1},{m}\n" for i, m in enumerate(markers))
    (folder / "x_image_collection-v2" / f"{panel_id}_ChannelKey.csv").write_text("\ufeff" + key, encoding="utf-8")
    tifffile.imwrite(folder / "x_image_collection-v2" / f"{panel_id}_DAPIcomposite.tif", stack, resolution=(PX_PER_UM, PX_PER_UM))
    tifffile.imwrite(folder / "x_segmentation_data" / f"{panel_id}_SegmentationMask.tif", labels)


@pytest.fixture
def kpmp_client(tmp_path):
    raw = tmp_path / "kpmp"
    for participant in PARTICIPANTS:
        write_participant(raw / participant.folder, participant.panel_id)
    artifacts = tmp_path / "artifacts"
    build(raw, tmp_path / "processed", artifacts, log=lambda _: None)
    settings = replace(make_settings(tmp_path), artifacts_dir=artifacts)
    with TestClient(create_app(settings)) as client:
        yield client, raw, tmp_path


def test_the_manifest_lists_both_participants_with_tiles_thresholds_and_no_clinical_values(kpmp_client):
    client, _, _ = kpmp_client
    manifest = client.get("/api/kpmp").json()
    assert manifest["dataset_id"] == "KPMP-CODEX"
    assert [p["participant_id"] for p in manifest["participants"]] == ["164-17", "31-10013"]
    first = manifest["participants"][0]
    assert first["role"] == "healthy reference" and first["pixel_size_um"] == pytest.approx(0.5)
    assert first["extent"]["x1"] == pytest.approx(32.0) and first["cells"] == 256
    assert first["clinical"] == {} and "not downloaded" in first["clinical_note"]
    assert {c["channel_id"] for c in first["channels"]} == {d[0] for d in DISPLAY}
    tile = first["channels"][0]["tiles"][0]
    response = client.get(f"/api/kpmp/files/{tile['path']}")
    assert response.status_code == 200 and response.content[:4] == b"RIFF"
    assert {t["source_participant_id"] for t in manifest["thresholds"]} == {"164-17"}
    assert len(manifest["results"]) == 4


def test_a_box_scopes_the_protein_audit_to_the_cells_whose_centroid_it_holds(kpmp_client):
    """Rows 0-3 of the cell grid (cells 0-63) lie at y < 8 µm: all Podocalyxin+, and cells 0-49 LRP2+, so 50 of 64."""
    client, _, _ = kpmp_client
    whole = client.get("/api/kpmp/31-10013/protein-audit", params={"population_marker": "Podocalyxin", "marker": "LRP2"}).json()
    assert whole["roi"] is None and whole["population_cells"] == 100
    boxed = client.get("/api/kpmp/31-10013/protein-audit",
                       params={"population_marker": "Podocalyxin", "marker": "LRP2", "x0": 0, "y0": 0, "x1": 32, "y1": 8}).json()
    assert boxed["roi"]["y1"] == 8 and boxed["population_cells"] == 64
    whole_cell = next(c for c in boxed["conditions"] if c["condition"] == "whole_cell")
    assert whole_cell["positive_cells"] == 50 and whole_cell["observed_share"] == pytest.approx(50 / 64)


def test_bad_requests_are_refused(kpmp_client):
    client, _, _ = kpmp_client
    assert client.get("/api/kpmp/99-1/protein-audit", params={"population_marker": "CD20", "marker": "UMOD"}).status_code == 404
    assert client.get("/api/kpmp/164-17/protein-audit", params={"population_marker": "CD20", "marker": "LRP2"}).status_code == 400
    assert client.get("/api/kpmp/164-17/protein-audit", params={"population_marker": "CD20", "marker": "UMOD", "x0": 5}).status_code == 400
    assert client.get("/api/kpmp/files/KPMP/../../secret.txt").status_code == 404


def test_the_build_is_reproducible(kpmp_client):
    _, raw, tmp_path = kpmp_client
    first = (tmp_path / "artifacts" / "KPMP" / "31-10013" / "audit_podocalyxin_lrp2.json").read_text()
    build(raw, tmp_path / "processed", tmp_path / "artifacts", log=lambda _: None)
    assert (tmp_path / "artifacts" / "KPMP" / "31-10013" / "audit_podocalyxin_lrp2.json").read_text() == first
