"""Seam 2: the committed GSE286184 descriptive disease contrasts and their figures.

The contrast results are committed artifacts (`make contrasts`). These tests check their shape and completeness,
never their outcome (ADR-0001).
"""

import json

import pytest
from fastapi.testclient import TestClient

from spatialscout.api import create_app

from .conftest import REPO, make_settings


@pytest.fixture
def client(tmp_path):
    settings = make_settings(tmp_path)
    settings = type(settings)(**{**settings.__dict__, "artifacts_dir": REPO / "artifacts", "processed_dir": tmp_path / "processed"})
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def index(client):
    response = client.get("/api/datasets/GSE286184/contrast-results")
    assert response.status_code == 200
    return response.json()


def test_the_contrasts_cover_four_diseases_with_the_run_configuration_citation_and_disclosure(index):
    assert {(c["disease"], c["control"]) for c in index["run_configuration"]["contrasts"]} == {
        ("DKD", "Control"), ("IgAN", "Control"), ("MCD", "Control"), ("MN", "Control")}
    assert index["run_configuration"]["rules"]["near_zero_band_log2"] == 0.1
    assert "GSE286184" in index["citation"]
    assert "22 sections from 19 donors" in index["section_disclosure"]
    assert len(index["sections_counted"]) == 21
    assert index["sections_left_out"] == [{"section_id": "GSM8720419", "reason": "duplicate_of GSM8720418"}]
    assert len(index["entries"]) == 4 * len(index["run_configuration"]["grid"])


def test_every_contrast_is_descriptive_with_its_rules_and_no_p_values(client, index):
    for entry in index["entries"]:
        result = client.get(f"/api/datasets/GSE286184/contrast-results/{entry['finding_id']}").json()
        text = json.dumps(result)
        assert "p_value" not in text and "confidence_interval" not in text
        assert result["inference_eligibility"] == "descriptive_only"
        assert result["rules"]["population_gate_min_cells"] == 20
        assert "22 sections from 19 donors" in result["section_disclosure"]
        assert "GSM8720419" not in {s["section_id"] for s in result["sections"]}
        if result["groups"]["disease"] == "IgAN":
            assert result["donor_distinctness"] == "counts_do_not_reconcile"
            assert result["sections_left_out"] == [{"section_id": "GSM8720419", "reason": "duplicate_of GSM8720418"}]
        assert all(v["condition"] != "structure_constrained" for v in result["per_section"])


def test_each_contrast_figure_is_served(client, index):
    entry = index["entries"][0]
    response = client.get(f"/api/datasets/GSE286184/contrast-results/{entry['finding_id']}/figure.png")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_the_audit_index_carries_the_section_disclosure(client):
    index = client.get("/api/datasets/GSE286184/audit-results").json()
    assert "22 sections from 19 donors" in index["section_disclosure"]
