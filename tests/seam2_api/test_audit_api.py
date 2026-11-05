"""Seam 2: the committed GSE286184 audit results, their figures and controls, and the live gate status of a box.

The audit results are committed artifacts (`make audit`), served without the validated tables. These tests check
their shape and completeness, never their outcome (ADR-0001).
"""

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
    response = client.get("/api/datasets/GSE286184/audit-results")
    assert response.status_code == 200
    return response.json()


def test_the_audit_results_count_21_distinct_sections_and_leave_the_duplicate_out(index):
    assert len(index["sections_counted"]) == 21
    assert index["sections_left_out"] == [{"section_id": "GSM8720419", "reason": "duplicate_of GSM8720418"}]
    assert "configs/exclusive_marker_pairs.json" in index["input_sha256"]


def test_the_demo_results_are_listed_each_with_a_figure_and_a_random_thinning_control(index):
    slugs = {e["slug"] for e in index["entries"]}
    assert {"hero-podocyte-lrp2-cubn", "hero-podocyte-lrp2-cubn-full-panel", "umod-b-cell"} <= slugs
    assert {e["cell_type"] for e in index["entries"] if e["measure"] == "co_expression_score"} >= {"Podocyte", "PT", "TAL", "B cell"}
    for entry in index["entries"]:
        assert entry["figure"]["path"].endswith(".png")
        assert entry["random_thinning_control_id"].startswith("ctl-")


def test_every_audit_number_comes_with_its_retention_and_expectations(client, index):
    for entry in index["entries"]:
        result = client.get(f"/api/datasets/GSE286184/audit-results/{entry['finding_id']}").json()
        assert result["marker_pairs"]["path"] == "configs/exclusive_marker_pairs.json"
        assert result["sections_left_out"] == [{"section_id": "GSM8720419", "reason": "duplicate_of GSM8720418"}]
        for section in result["sections"]:
            for value in section["conditions"]:
                if value["observed_value"] is None:
                    continue
                for field in ("retention", "expectation_home_matched", "expectation_cell_matched"):
                    assert value[field] is not None or field in value["missing_reasons"], (entry["slug"], section["section_id"], field)
        for pooled in result["pooled"]:
            if pooled["observed_value"] is not None:
                assert pooled["retention"] is not None and pooled["expectation_home_matched"] is not None


def test_the_hero_label_sensitivity_check_reports_both_rules_with_cell_counts(client, index):
    hero = next(e for e in index["entries"] if e["slug"] == "hero-podocyte-lrp2-cubn")

    check = client.get(f"/api/datasets/GSE286184/audit-results/{hero['finding_id']}/label-sensitivity-check").json()

    assert [arm["label_rule_id"] for arm in check["arms"]] == ["nphs1-anchored-v1", "full-panel-v1"]
    assert all(arm["cells_labelled"] > 0 and len(arm["cells_labelled_by_section"]) == 21 for arm in check["arms"])
    assert check["cells_in_both"] + check["cells_only_first"] == check["arms"][0]["cells_labelled"]


def test_a_results_composite_figure_is_served_as_a_png(client, index):
    response = client.get(f"/api/datasets/GSE286184/audit-results/{index['entries'][0]['finding_id']}/figure.png")

    assert response.headers["content-type"] == "image/png"
    assert response.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_an_unknown_audit_result_is_not_found(client):
    assert client.get("/api/datasets/GSE286184/audit-results/fnd-0000").status_code == 404


def test_the_verification_benchmark_reports_caught_and_flagged_counts(client):
    bench = client.get("/api/datasets/GSE286184/verification-benchmark").json()

    assert (bench["valid_claims"], bench["injected_claims"]) == (21, 147)
    assert bench["injected_caught"] == bench["injected_claims"] == 147
    assert (bench["valid_flagged"], bench["valid_flagged_visual_only"]) == (7, 7)
    assert (bench["structural_false"], bench["numerical_false"]) == (0, 0)


def test_the_verification_benchmark_is_not_found_without_committed_results(client):
    assert client.get("/api/datasets/synthetic/verification-benchmark").status_code == 404


def test_gate_status_of_a_box_on_the_synthetic_section(client):
    """SYN-01: podocytes C01 (46, 86), C02 (70, 92), C03 (78, 70); only C03 carries LRP2 (4 molecules)."""
    whole = client.get("/api/sections/SYN-01/gate-status", params={"cell_type": "Podocyte", "genes": ["LRP2"]}).json()
    left = client.get(
        "/api/sections/SYN-01/gate-status",
        params={"cell_type": "Podocyte", "genes": ["LRP2", "NPHS1"], "x0": 60, "y0": 0, "x1": 0, "y1": 150},
    ).json()

    assert (whole["cells"], whole["molecules"], whole["passes_population_gate"]) == (3, 4, False)
    assert left["roi"] == {"section_id": "SYN-01", "x0": 0, "y0": 0, "x1": 60, "y1": 150}
    assert (left["cells"], left["molecules"]) == (1, 20)
    assert "below population gate" in left["status"]
