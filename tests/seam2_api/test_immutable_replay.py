"""Seam 2: immutable replay streams a recorded investigation's events verbatim, with their original timestamps,
under its original id, and never runs a tool, calls a model or writes a file."""

import hashlib
import json

from fastapi.testclient import TestClient

from spatialscout.api import create_app

from .conftest import RECORDED_QUESTION, REPO, make_settings

RECORDED = REPO / "fixtures" / "recordings" / "syn01-podocyte-lrp2" / "investigation"


def recorded_lines():
    return (RECORDED / "events.jsonl").read_text().splitlines()


def fingerprint():
    return {p.relative_to(RECORDED).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(RECORDED.rglob("*")) if p.is_file()}


def replay(client):
    response = client.post("/api/investigations", json={"question": RECORDED_QUESTION, "run_mode": "immutable_replay"})
    assert response.status_code == 201, response.text
    return response.json()


def raw_stream(client, investigation_id, after_seq=0):
    with client.stream("GET", f"/api/investigations/{investigation_id}/events", params={"after_seq": after_seq}) as stream:
        return [line.removeprefix("data:").lstrip() for line in stream.iter_lines() if line.startswith("data:")]


def test_immutable_replay_streams_the_recorded_events_verbatim(client):
    snapshot = replay(client)

    streamed = raw_stream(client, snapshot["investigation_id"])

    assert streamed == recorded_lines()
    first = json.loads(recorded_lines()[0])
    assert snapshot["investigation_id"] == first["investigation_id"]
    assert [e["recorded_at_utc"] for e in snapshot["events"]] == [json.loads(line)["recorded_at_utc"] for line in recorded_lines()]


def test_immutable_replay_is_labelled_and_complete(client):
    snapshot = replay(client)

    assert (snapshot["run_mode"], snapshot["status"]) == ("immutable_replay", "complete")
    assert snapshot["replay"]["question"] == RECORDED_QUESTION
    assert snapshot["package"] is not None
    assert "immutable_replay" in client.get("/api/mode").json()["available_run_modes"]


def test_immutable_replay_reconnects_with_after_seq(client):
    investigation_id = replay(client)["investigation_id"]

    assert raw_stream(client, investigation_id, after_seq=3) == recorded_lines()[3:]


def test_approving_a_replay_changes_nothing_and_no_recorded_file_is_written(client):
    before = fingerprint()
    snapshot = replay(client)

    after_approval = client.post(f"/api/investigations/{snapshot['investigation_id']}/approve").json()
    raw_stream(client, snapshot["investigation_id"])
    package = client.get(f"/api/investigations/{snapshot['investigation_id']}/package")

    assert after_approval["events"] == snapshot["events"]
    assert package.status_code == 200
    assert fingerprint() == before


def test_a_replayed_investigation_opens_by_id_after_a_restart(tmp_path):
    with TestClient(create_app(make_settings(tmp_path))) as first:
        investigation_id = replay(first)["investigation_id"]

    with TestClient(create_app(make_settings(tmp_path))) as after_restart:
        snapshot = after_restart.get(f"/api/investigations/{investigation_id}").json()

    assert (snapshot["run_mode"], snapshot["status"], len(snapshot["events"])) == ("immutable_replay", "complete", len(recorded_lines()))
