"""Seam 2: an investigation driven through the HTTP/SSE API on recorded model responses."""

import json

from .conftest import RECORDED_QUESTION


def start(client, question=RECORDED_QUESTION):
    """Post a question and return the investigation once planning has finished."""
    response = client.post("/api/investigations", json={"question": question})
    assert response.status_code == 201, response.text
    investigation_id = response.json()["investigation_id"]
    events = read_events(client, investigation_id, until={"plan_proposed", "error"})
    assert events, "no event arrived"
    return client.get(f"/api/investigations/{investigation_id}").json()


def read_events(client, investigation_id, after_seq=0, until=frozenset({"package_ready", "error"})):
    """Read the SSE stream until an event whose type is in `until`, then disconnect."""
    events = []
    with client.stream("GET", f"/api/investigations/{investigation_id}/events", params={"after_seq": after_seq}) as stream:
        for line in stream.iter_lines():
            if line.startswith("data:"):
                events.append(json.loads(line.removeprefix("data:")))
                if events[-1]["type"] in until:
                    break
    return events


def test_a_question_gets_the_recorded_plan_and_nothing_runs_before_approval(client):
    investigation = start(client)

    assert investigation["status"] == "awaiting_approval"
    assert [step["tool"] for step in investigation["plan"]["steps"]] == ["audit_population"]
    assert [event["type"] for event in investigation["events"]] == ["plan_proposed"]


def test_a_question_without_stored_responses_fails_instead_of_calling_a_model(client):
    investigation = start(client, "Is UMOD higher in B cells in DKD?")

    assert investigation["status"] == "failed"
    assert investigation["plan"] is None
    last = investigation["events"][-1]
    assert (last["type"], last["code"]) == ("error", "replay_miss")
