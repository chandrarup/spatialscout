"""Measured depth through the API, on a SYN-01 sidecar with known z: every molecule at z = 10 + (index mod 5), except
the first, which has none. The sidecar sits in its own directory; the synthetic section and its recordings are
untouched."""

import hashlib
import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from spatialscout.api import create_app
from spatialscout.contracts import DepthSource
from spatialscout.engine.depth import build_depth_sidecar

from .conftest import REPO, make_settings

BOX = {"section_id": "SYN-01", "x0": 0, "y0": 0, "x1": 200, "y1": 150}


@pytest.fixture
def depth_client(tmp_path):
    molecules = pd.read_csv(REPO / "fixtures" / "synthetic" / "SYN-01" / "molecules.csv", dtype={"molecule_id": str})
    z = 10.0 + (np.arange(len(molecules)) % 5)
    z[0] = np.nan
    raw = pd.DataFrame({"transcript_id": molecules["molecule_id"], "x_location": molecules["x"], "y_location": molecules["y"], "z_location": z})
    table, stats = build_depth_sidecar(molecules, raw)
    folder = tmp_path / "depth" / "SYN-01"
    folder.mkdir(parents=True)
    table.to_parquet(folder / "depth.parquet", index=False)
    source = DepthSource(
        dataset_id="synthetic", section_id="SYN-01", coordinate_note="test", raw_file="built in the test", raw_sha256="-", molecules_sha256="-",
        sidecar_sha256=hashlib.sha256((folder / "depth.parquet").read_bytes()).hexdigest(), **stats,
    )
    (folder / "depth.json").write_text(source.model_dump_json())
    settings = make_settings(tmp_path)
    settings = type(settings)(**{**settings.__dict__, "depth_dir": tmp_path / "depth"})
    with TestClient(create_app(settings)) as client:
        yield client, len(molecules)


def test_the_sidecar_round_trips_with_its_missing_depth(depth_client):
    client, n = depth_client
    assert client.get("/api/depth/sections").json() == ["SYN-01"]
    source = client.get("/api/sections/SYN-01/depth").json()
    assert (source["molecules"], source["with_depth"], source["missing_depth"]) == (n, n - 1, 1)
    assert (source["z_min"], source["z_max"], source["units"]) == (10.0, 14.0, "µm")


def test_profile_bins_sum_to_the_full_data_totals(depth_client):
    client, _ = depth_client
    profile = client.post("/api/sections/SYN-01/depth-profile", json={"region": BOX, "genes": ["LRP2", "NPHS1"], "bin_um": 1, "cell_type": "Podocyte"}).json()
    assert profile["kind"] == "new_descriptive_depth_exploration"
    for gene in profile["genes"]:
        for condition in profile["conditions"]:
            assert sum(b["counts"][gene][condition] for b in profile["bins"]) == profile["totals"][gene][condition]
    # SYN-01's known answer: podocyte LRP2 goes from 4 to 0 under nucleus-only (all four have a z).
    assert profile["totals"]["LRP2"]["default"] == 4 and profile["totals"]["LRP2"]["nucleus_only"] == 0
    # Half-open bins, the last one closed: z = 14 counts in [13, 14].
    assert [(b["z0"], b["z1"]) for b in profile["bins"]] == [(10.0, 11.0), (11.0, 12.0), (12.0, 13.0), (13.0, 14.0)]
    everything = client.post("/api/sections/SYN-01/depth-profile", json={"region": BOX, "genes": ["LRP2"], "bin_um": 1}).json()
    lrp2 = pd.read_csv(REPO / "fixtures" / "synthetic" / "SYN-01" / "molecules.csv").reset_index()
    lrp2 = lrp2[(lrp2.gene == "LRP2") & (lrp2["index"] > 0)]
    assert everything["bins"][-1]["counts"]["LRP2"]["all"] == int((lrp2["index"] % 5 >= 3).sum())


def test_points_slice_by_depth_and_sampling_keeps_the_counts(depth_client):
    client, _ = depth_client
    params = {**{k: v for k, v in BOX.items() if k != "section_id"}, "genes": ["LRP2", "NPHS1"]}
    full = client.get("/api/sections/SYN-01/depth/points", params=params).json()
    sliced = client.get("/api/sections/SYN-01/depth/points", params={**params, "z0": 12, "z1": 12.5}).json()
    sampled = client.get("/api/sections/SYN-01/depth/points", params={**params, "budget": 3}).json()

    assert all(12 <= z <= 12.5 for z in sliced["z"]) and sliced["eligible"] < full["eligible"]
    assert (sampled["total_in_box"], sampled["eligible"], sampled["displayed"]) == (full["total_in_box"], full["eligible"], 3)


def test_a_section_without_a_sidecar_says_which_sections_have_one(client):
    response = client.get("/api/sections/SYN-01/depth")
    assert response.status_code == 404
    assert "sections with measured depth" in response.json()["detail"]


def test_a_tampered_sidecar_is_refused(depth_client, tmp_path):
    client, _ = depth_client
    meta = tmp_path / "depth" / "SYN-01" / "depth.json"
    meta.write_text(json.dumps({**json.loads(meta.read_text()), "sidecar_sha256": "0" * 64}))
    response = client.post("/api/sections/SYN-01/depth-profile", json={"region": BOX, "genes": ["LRP2"]})
    assert response.status_code == 409
