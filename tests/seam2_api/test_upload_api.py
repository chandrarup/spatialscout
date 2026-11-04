"""Bring your own sections: uploaded Xenium output is audited by the same engine and nothing is kept."""

from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from spatialscout.api import create_app

from .conftest import make_settings

REPO = Path(__file__).resolve().parents[2]
SAMPLE = REPO / "fixtures" / "upload_sample"


def app_client(tmp_path):
    return TestClient(create_app(replace(make_settings(tmp_path), artifacts_dir=REPO / "artifacts")))


def test_uploaded_xenium_sections_are_audited_and_nothing_is_written(tmp_path):
    sections = sorted(d for d in SAMPLE.iterdir() if d.is_dir())
    files = [("transcripts", (f"{d.name}.parquet", (d / "transcripts.parquet").read_bytes())) for d in sections]
    files += [("cells", (f"{d.name}.csv.gz", (d / "cells.csv.gz").read_bytes())) for d in sections]
    with app_client(tmp_path) as client:
        response = client.post("/api/upload/audit", data={"cell_type": "Podocyte", "genes": "NPHS1"}, files=files)
    assert response.status_code == 200, response.text
    audit = response.json()
    assert audit["retained"] is False and "discarded" in audit["handling"]
    assert audit["result"]["label"] == "stable" and len(audit["result"]["eligible_section_ids"]) == 3
    assert audit["figure_svg"].startswith("<?xml") and "3 eligible sections" in audit["legend"]
    assert [s["validation"]["molecules_kept"] > 0 for s in audit["sections"]] == [True, True, True]
    written = [p for p in tmp_path.rglob("*") if p.is_file()]
    assert written == [], f"the upload left files behind: {written}"


def test_links_must_be_https_and_files_must_pair(tmp_path):
    with app_client(tmp_path) as client:
        insecure = client.post("/api/upload/audit", data={"cell_type": "PT", "genes": "LRP2", "transcripts_url": "http://x/t.parquet", "cells_url": "http://x/c.csv"})
        assert insecure.status_code == 400 and insecure.json()["detail"]["code"] == "bad_url"
        d = next(p for p in SAMPLE.iterdir() if p.is_dir())
        unpaired = client.post("/api/upload/audit", data={"cell_type": "PT", "genes": "LRP2"},
                               files=[("transcripts", ("t.parquet", (d / "transcripts.parquet").read_bytes())), ("transcripts", ("u.parquet", b"x")),
                                      ("cells", ("c.csv.gz", (d / "cells.csv.gz").read_bytes()))])
        assert unpaired.status_code == 400 and unpaired.json()["detail"]["code"] == "unpaired"
