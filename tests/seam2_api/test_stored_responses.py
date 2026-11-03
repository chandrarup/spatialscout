"""Seam 2: stored model responses are keyed by the request plus the tool version and artifact checksum it was
built from, so a changed tool or a changed artifact never gets a stale response (ADR-0003)."""

import csv
import dataclasses
import shutil

from fastapi.testclient import TestClient

from spatialscout.agent import DEFAULT_REGISTRY
from spatialscout.api import create_app

from .conftest import REPO, make_settings
from .test_investigation_api import approve, read_events, start


def test_a_changed_tool_version_misses_the_stored_plan(tmp_path, monkeypatch):
    tool = DEFAULT_REGISTRY.get("audit_population")
    monkeypatch.setitem(DEFAULT_REGISTRY._tools, tool.name, dataclasses.replace(tool, version=tool.version + "-changed"))
    with TestClient(create_app(make_settings(tmp_path))) as client:
        investigation = start(client)

    assert [(e["type"], e.get("code")) for e in investigation["events"]] == [("model_call", None), ("error", "replay_miss")]
    assert investigation["events"][0]["call"]["error_code"] == "replay_miss"


def test_a_changed_artifact_misses_the_stored_claim_draft(tmp_path):
    """Move one LRP2 molecule of a podocyte onto its nucleus: the audit result's checksum changes, so the
    plan (built from the unchanged capability report) still replays but the claim draft does not."""
    fixtures = tmp_path / "fixtures"
    shutil.copytree(REPO / "fixtures", fixtures)
    molecules = fixtures / "synthetic" / "SYN-01" / "molecules.csv"
    rows = list(csv.DictReader(molecules.open()))
    moved = next(row for row in rows if row["gene"] == "LRP2" and row["cell_id"] == "C03" and row["overlaps_nucleus"] == "0")
    moved.update(overlaps_nucleus="1", nucleus_distance="0.000")
    with molecules.open("w", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    settings = dataclasses.replace(make_settings(tmp_path), fixtures_dir=fixtures, recordings_dir=REPO / "fixtures" / "recordings")

    with TestClient(create_app(settings)) as client:
        investigation_id = start(client)["investigation_id"]
        approve(client, investigation_id)
        events = read_events(client, investigation_id)

    calls = [(e["call"]["purpose"], e["call"]["error_code"]) for e in events if e["type"] == "model_call"]
    assert calls == [("plan", None), ("claim_draft", "replay_miss")]
    assert (events[-1]["type"], events[-1]["code"]) == ("error", "replay_miss")
