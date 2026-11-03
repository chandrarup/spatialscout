"""Seam 2: each SSE connection closes after a bounded window, so a deployment that cuts requests (Modal, at 150 s)
never cuts a stream mid-event, and a client that reconnects with `after_seq` sees every event exactly once."""

import dataclasses
import json

import pytest
from fastapi.testclient import TestClient

from spatialscout.api import create_app

from .conftest import make_settings
from .test_investigation_api import FULL_SEQUENCE, approve, start

WINDOW_SECONDS = 0.3


@pytest.fixture
def windowed_client(tmp_path):
    settings = dataclasses.replace(make_settings(tmp_path), stream_window_seconds=WINDOW_SECONDS)
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def read_one_connection(client, investigation_id, after_seq=0, headers=None):
    """Read one SSE connection until the server ends it; return its events."""
    events = []
    with client.stream(
        "GET", f"/api/investigations/{investigation_id}/events", params={"after_seq": after_seq}, headers=headers or {}
    ) as stream:
        for line in stream.iter_lines():
            if line.startswith("data:"):
                events.append(json.loads(line.removeprefix("data:")))
    return events


@pytest.mark.timeout(5)
def test_a_stream_waiting_on_approval_ends_when_its_window_closes(windowed_client):
    investigation_id = start(windowed_client)["investigation_id"]

    events = read_one_connection(windowed_client, investigation_id)

    assert [event["type"] for event in events] == ["plan_proposed"]


@pytest.mark.timeout(10)
def test_an_investigation_longer_than_the_window_streams_completely_through_reconnects(windowed_client):
    investigation_id = start(windowed_client)["investigation_id"]
    seen = read_one_connection(windowed_client, investigation_id)  # the window closes while approval is pending
    approve(windowed_client, investigation_id)

    for _ in range(20):
        if seen and seen[-1]["type"] in {"package_ready", "error"}:
            break
        seen += read_one_connection(windowed_client, investigation_id, after_seq=seen[-1]["seq"])

    assert [event["seq"] for event in seen] == [1, 2, 3, 4, 5, 6]
    assert [event["type"] for event in seen] == FULL_SEQUENCE


@pytest.mark.timeout(5)
def test_a_browser_reconnect_with_last_event_id_resumes_after_that_event(windowed_client):
    investigation_id = start(windowed_client)["investigation_id"]
    approve(windowed_client, investigation_id)

    events = read_one_connection(windowed_client, investigation_id, headers={"Last-Event-ID": "2"})

    assert [event["seq"] for event in events] == [3, 4, 5, 6]
