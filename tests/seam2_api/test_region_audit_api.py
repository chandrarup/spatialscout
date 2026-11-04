"""A box drawn on an RNA section is audited by the same engine operation the agent's tool runs, scoped to exactly
that box, with no model call.

SYN-01 (scripts/build_synthetic_section.py): podocytes C01 (46, 86), C02 (70, 92), C03 (78, 70); only C03 carries
LRP2, 4 molecules in its expansion zone, which nucleus-only excludes.
"""


def _audit(client, **box):
    return client.post(
        "/api/sections/SYN-01/region-audit",
        json={"cell_type": "Podocyte", "genes": ["LRP2"], "region": {"section_id": "SYN-01", **box}},
    )


def _values(result, condition):
    section = result["sections"][0]
    return section["cells_labelled"], next(c for c in section["conditions"] if c["condition"] == condition)


def test_the_box_reaches_the_calculation_and_scopes_it(client):
    result = _audit(client, x0=60, y0=20, x1=100, y1=130).json()

    assert result["roi"] == {"section_id": "SYN-01", "x0": 60, "y0": 20, "x1": 100, "y1": 130}
    cells, default = _values(result, "default")
    _, nucleus = _values(result, "nucleus_only")
    assert cells == 2
    assert (default["molecules"], default["observed_value"]) == (4, 0.5)
    assert (nucleus["molecules"], nucleus["observed_value"]) == (0, 0.0)


def test_moving_the_box_changes_the_result_where_the_data_differ(client):
    left = _audit(client, x0=0, y0=0, x1=60, y1=150).json()

    cells, default = _values(left, "default")
    assert cells == 1
    assert default["molecules"] == 0


def test_a_single_small_box_gets_an_honest_insufficient_evidence_label(client):
    result = _audit(client, x0=60, y0=0, x1=100, y1=150).json()

    assert result["label"] == "insufficient_evidence"
    assert result["eligible_section_ids"] == []


def test_an_empty_or_mismatched_box_is_refused(client):
    assert _audit(client, x0=10, y0=10, x1=10, y1=80).status_code == 422
    wrong = client.post(
        "/api/sections/SYN-01/region-audit",
        json={"cell_type": "Podocyte", "genes": ["LRP2"], "region": {"section_id": "GSM8720426", "x0": 0, "y0": 0, "x1": 50, "y1": 50}},
    )
    assert wrong.status_code == 422


def test_a_box_partly_outside_the_section_is_clamped_to_it(client):
    result = _audit(client, x0=60, y0=-50, x1=100, y1=500).json()

    roi = result["roi"]
    assert (roi["x0"], roi["x1"]) == (60, 100)
    assert 0 <= roi["y0"] < roi["y1"] <= 150
    assert _values(result, "default")[0] == 2
