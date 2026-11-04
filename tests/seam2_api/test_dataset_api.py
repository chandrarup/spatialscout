"""Seam 2: what the dataset panel and the viewer read about GSE286184 and the synthetic section.

The GSE286184 manifest, capability report and label rules are committed artifacts, so they are served even where
the validated tables are absent (here: an empty processed directory), as on a fresh checkout or a deployment.
"""

import base64

import numpy as np
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


def decode(column, dtype):
    assert column["dtype"] == dtype
    return np.frombuffer(base64.b64decode(column["data"]), dtype=np.dtype(dtype).newbyteorder("<"))


def test_both_datasets_are_listed(client):
    assert [d["dataset_id"] for d in client.get("/api/datasets").json()] == ["GSE286184", "synthetic"]


def test_the_manifest_names_22_sections_by_group_with_their_filters_and_citation(client):
    manifest = client.get("/api/datasets/GSE286184").json()

    groups = {}
    for section in manifest["sections"]:
        groups.setdefault(section["group"], []).append(section["name"])
    assert groups == {
        "Control": ["x1", "x2", "x6"],
        "DKD": ["x3", "x4", "x5", "x7", "x8", "x9"],
        "IgAN": ["x10", "x11", "x12", "x13"],
        "MCD": ["x14", "x15", "x16", "x17"],
        "MN": ["x18", "x19", "x20", "x21", "x22"],
    }
    assert (manifest["filters"]["min_qv"], manifest["filters"]["panel_genes_only"], len(manifest["panel"])) == (20, True, 50)
    assert "GSE286184" in manifest["citation"] and manifest["synthetic"] is False
    assert len(manifest["files"]) == 66 and all(len(f["sha256"]) == 64 for f in manifest["files"])


def test_every_molecule_read_is_kept_or_counted_in_the_manifest(client):
    for section in client.get("/api/datasets/GSE286184").json()["sections"]:
        v = section["validation"]
        dropped = v["malformed_molecules"] + v["duplicate_molecules"] + v["below_quality"] + v["not_in_panel"]
        assert v["molecules_read"] == v["molecules_kept"] + dropped
        assert section["molecules"] == v["molecules_kept"]


def test_the_section_deposited_twice_is_marked_as_a_duplicate(client):
    sections = {s["section_id"]: s for s in client.get("/api/datasets/GSE286184").json()["sections"]}

    assert sections["GSM8720419"]["duplicate_of"] == "GSM8720418"
    assert [sid for sid, s in sections.items() if s["duplicate_of"]] == ["GSM8720419"]


def test_the_capability_report_states_what_is_supported_unavailable_and_descriptive_only(client):
    report = client.get("/api/datasets/GSE286184/capability-report").json()

    status = {c["capability"]: c["status"] for c in report["checks"]}
    assert {k for k, v in status.items() if v == "supported"} == {"coordinate_inspection", "assignment_audit", "disease_contrast", "distinct_sections"}
    assert {k for k, v in status.items() if v == "unavailable"} == {"cell_boundaries", "images", "deposited_cell_type_labels", "donor_mapping"}
    contrasts = {c["groups"]["disease"]: c for c in report["contrasts"]}
    assert set(contrasts) == {"DKD", "IgAN", "MCD", "MN"}
    assert {c["inference_eligibility"] for c in contrasts.values()} == {"descriptive_only"}
    assert {d for d, c in contrasts.items() if c["donor_distinctness"] == "repeat_donor_in_group"} == {"DKD", "MCD", "MN"}
    # x10 and x11 are byte-identical deposits: IgAN has 3 distinct sections against 4 published patients, so the
    # published counts no longer show it donor-distinct.
    igan = contrasts["IgAN"]
    assert igan["donor_distinctness"] == "counts_do_not_reconcile"
    assert "conditionally donor-distinct" not in igan["donor_distinctness_statement"]
    assert (igan["excluded_section_ids"], len(igan["disease_section_ids"]), igan["disease_donors_published"]) == (["GSM8720419"], 3, 4)
    assert "GSM8720419" in igan["inference_reason"]


def test_the_capability_report_counts_21_distinct_sections_and_names_the_duplicate(client):
    checks = {c["capability"]: c for c in client.get("/api/datasets/GSE286184/capability-report").json()["checks"]}

    assert "21 distinct sections" in checks["distinct_sections"]["reason"]
    assert "GSM8720419" in checks["distinct_sections"]["reason"] and "GSM8720418" in checks["distinct_sections"]["reason"]


def test_the_label_rules_are_frozen_with_counts_under_each_rule(client):
    rules = client.get("/api/datasets/GSE286184/label-rules").json()

    assert [r["label_rule_id"] for r in rules["rules"]] == ["full-panel-v1", "nphs1-anchored-v1"]
    assert rules["gene_scale_sections"] == ["GSM8720409", "GSM8720410", "GSM8720414"]
    assert len(rules["sections"]) == 22
    for counts in rules["sections"].values():
        assert counts["differing_cells"] == sum(counts["differing"].values())
        for per_type in counts["cell_types"].values():
            assert sum(per_type.values()) == counts["cells"]


def test_a_section_whose_tables_are_not_ingested_says_how_to_ingest_it(client):
    response = client.get("/api/sections/GSM8720410/region-view/packed")

    assert response.status_code == 409
    assert "make data" in response.json()["detail"]


def test_the_packed_region_view_ships_the_synthetic_section_as_typed_columns(client):
    view = client.get("/api/sections/SYN-01/region-view/packed").json()
    molecules, cells = view["molecules"], view["cells"]

    assert (molecules["count"], cells["count"]) == (300, 12)
    assert len(decode(molecules["x"], "float32")) == len(decode(molecules["y"], "float32")) == 300
    bits = decode(molecules["inclusion_bits"], "uint8")
    default, nucleus_only = (1 << molecules["condition_bits"][c] for c in ("default", "nucleus_only"))
    # 240 assigned molecules count under the default condition; nucleus-only keeps the 180 nuclear ones.
    assert (int(((bits & default) > 0).sum()), int(((bits & nucleus_only) > 0).sum())) == (240, 180)
    assert int((decode(molecules["cell_index"], "int32") == -1).sum()) == 60
