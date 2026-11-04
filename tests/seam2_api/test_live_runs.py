"""Seam 2: live runs through the HTTP/SSE API, with fake providers behind the model transport.

Covers the live gate (passcode and daily budget), the audit log's live/stored marking, failover from Baseten
to Fireworks, reasoning-model defaults, the bounded repair, and keys never leaving the backend.
"""

import dataclasses
import io
import json
import logging
import zipfile

from fastapi.testclient import TestClient

from spatialscout.api import create_app
from spatialscout.settings import LiveSettings

from .conftest import RECORDED_QUESTION, make_settings
from .fake_providers import FAKE_KEYS, FAKE_PRICES, PASSCODE, FakeProviders, fake_keys
from .test_investigation_api import FULL_SEQUENCE, approve, read_events

LIVE = {"X-Live-Passcode": PASSCODE}


def live_app(tmp_path, providers: FakeProviders, budget_usd: float = 10.0):
    settings = dataclasses.replace(
        make_settings(tmp_path),
        live=LiveSettings(passcode=PASSCODE, daily_budget_usd=budget_usd, spend_dir=tmp_path / "spend"),
    )
    return create_app(settings, model_transport=providers.transport(), prices=FAKE_PRICES, api_keys=fake_keys())


def start_live(client, headers=LIVE, question=RECORDED_QUESTION):
    return client.post("/api/investigations", json={"question": question, "run_mode": "live"}, headers=headers)


def run_live(client):
    """Start a live investigation, approve its plan and read every event to the end."""
    response = start_live(client)
    assert response.status_code == 201, response.text
    investigation_id = response.json()["investigation_id"]
    planned = read_events(client, investigation_id, until={"plan_proposed", "error"})
    if planned[-1]["type"] == "error":
        return investigation_id, planned
    approve(client, investigation_id)
    return investigation_id, read_events(client, investigation_id)


def model_calls(events):
    return [event["call"] for event in events if event["type"] == "model_call"]


def test_a_live_run_without_the_passcode_is_refused_and_calls_no_model(tmp_path):
    providers = FakeProviders()
    with TestClient(live_app(tmp_path, providers)) as client:
        missing = start_live(client, headers={})
        wrong = start_live(client, headers={"X-Live-Passcode": "guess"})

    assert (missing.status_code, wrong.status_code) == (403, 403)
    assert providers.sent == []
    assert not list((tmp_path / "investigations").glob("inv-*"))


def test_a_live_run_streams_to_a_package_and_its_audit_log_marks_every_response_live(tmp_path):
    providers = FakeProviders()
    with TestClient(live_app(tmp_path, providers)) as client:
        investigation_id, events = run_live(client)
        snapshot = client.get(f"/api/investigations/{investigation_id}").json()
        package = zipfile.ZipFile(io.BytesIO(client.get(f"/api/investigations/{investigation_id}/package").content))

    assert [event["type"] for event in events] == FULL_SEQUENCE
    audit = [json.loads(line) for line in package.read("audit_log.jsonl").decode().splitlines()]
    # a live run of a recorded question is still live: it carries no recording's replay label
    assert (snapshot["run_mode"], snapshot["replay"]) == ("live", None)
    assert json.loads(package.read("manifest.json"))["replay"] is None
    assert audit[0]["kind"] == "investigation_started" and audit[0]["payload"]["recording_id"] is None
    calls = [entry["payload"] for entry in audit if entry["kind"] == "model_call"]
    assert [(c["purpose"], c["source"], c["run_mode"]) for c in calls] == [
        ("plan", "live", "live"), ("follow_up", "live", "live"), ("claim_draft", "live", "live"),
    ]
    assert [(c["provider"], c["model"]) for c in calls] == [
        ("meta", "muse-wonder-1.0"), ("meta", "muse-spark-1.3"), ("baseten", "meta-models/muse-spark-open"),
    ]
    assert [c["estimated_cost_usd"] for c in calls] == [1.0, 1.0, 1.0]  # the fake price: $1.00 per call


def test_a_cached_tool_rerun_marks_every_response_stored(client):
    response = client.post("/api/investigations", json={"question": RECORDED_QUESTION})
    investigation_id = response.json()["investigation_id"]
    read_events(client, investigation_id, until={"plan_proposed"})
    approve(client, investigation_id)

    calls = model_calls(read_events(client, investigation_id))

    assert [(c["source"], c["run_mode"], c["estimated_cost_usd"]) for c in calls] == [
        ("replay", "cached_tool_rerun", None), ("replay", "cached_tool_rerun", None), ("replay", "cached_tool_rerun", None),
    ]


def test_a_live_run_records_its_responses_so_they_can_be_replayed(tmp_path):
    with TestClient(live_app(tmp_path, FakeProviders())) as client:
        investigation_id, _ = run_live(client)

    recording = json.loads((tmp_path / "investigations" / investigation_id / "recording.json").read_text())
    assert recording["info"]["origin"] == "live"
    assert [call["purpose"] for call in recording["calls"]] == ["plan", "follow_up", "claim_draft"]


def test_live_calls_use_the_reasoning_model_defaults(tmp_path):
    providers = FakeProviders()
    with TestClient(live_app(tmp_path, providers)) as client:
        run_live(client)

    assert len(providers.sent) == 3
    for sent in providers.sent:
        assert sent.body["max_tokens"] >= 2000
        assert sent.body["reasoning_effort"] == "low"
        assert sent.body["response_format"]["type"] == "json_schema"


def test_empty_content_cut_off_by_the_token_cap_is_reported_as_an_error(tmp_path):
    with TestClient(live_app(tmp_path, FakeProviders(finish_reason="length"))) as client:
        investigation_id, events = run_live(client)

    assert (events[-1]["type"], events[-1]["code"]) == ("error", "model_output_truncated")
    assert model_calls(events)[0]["finish_reason"] == "length"
    assert model_calls(events)[0]["error_code"] == "model_output_truncated"


def test_a_failing_baseten_call_fails_over_to_fireworks(tmp_path):
    providers = FakeProviders(status={"inference.baseten.co": 503})
    with TestClient(live_app(tmp_path, providers)) as client:
        _, events = run_live(client)

    assert [event["type"] for event in events] == FULL_SEQUENCE
    draft = model_calls(events)[2]
    assert (draft["provider"], draft["served_by"], draft["failover_from"]) == ("baseten", "fireworks", "baseten")
    assert [s.body["model"] for s in providers.calls_to("fireworks")] == ["accounts/fireworks/models/muse-spark-open"]


def test_a_baseten_refusal_of_the_request_itself_does_not_fail_over(tmp_path):
    providers = FakeProviders(status={"inference.baseten.co": 400})
    with TestClient(live_app(tmp_path, providers)) as client:
        _, events = run_live(client)

    assert (events[-1]["type"], events[-1]["code"]) == ("error", "provider_error")
    assert providers.calls_to("fireworks") == []


def test_an_invalid_structured_output_gets_one_repair_attempt(tmp_path):
    providers = FakeProviders()
    plan = providers._answer("muse-wonder-1.0")
    providers.answers["muse-wonder-1.0"] = ['{"summary": "missing every other field"}', plan]
    with TestClient(live_app(tmp_path, providers)) as client:
        _, events = run_live(client)

    assert [c["purpose"] for c in model_calls(events)] == ["plan", "plan_repair", "follow_up", "claim_draft"]
    repair = providers.sent[1].body["messages"]
    assert [m["role"] for m in repair[-2:]] == ["assistant", "user"]
    assert "does not match the response schema" in repair[-1]["content"]


def test_a_second_invalid_structured_output_fails_the_investigation(tmp_path):
    providers = FakeProviders(answers={"muse-wonder-1.0": "not json at all"})
    with TestClient(live_app(tmp_path, providers)) as client:
        _, events = run_live(client)

    assert (events[-1]["type"], events[-1]["code"]) == ("error", "model_output_invalid")
    assert len(providers.sent) == 2  # the call and its one repair, never more


def test_a_live_run_stops_when_the_next_call_would_exceed_the_budget(tmp_path):
    providers = FakeProviders()
    with TestClient(live_app(tmp_path, providers, budget_usd=1.5)) as client:
        _, events = run_live(client)

    assert (events[-1]["type"], events[-1]["code"]) == ("error", "budget_exhausted")
    assert len(providers.sent) == 1  # the $1.00 plan fits; the $1.00 claim draft does not


def test_a_live_run_is_refused_once_the_budget_is_spent(tmp_path):
    providers = FakeProviders()
    with TestClient(live_app(tmp_path, providers, budget_usd=3.0)) as client:
        run_live(client)
        refused = start_live(client)

    assert refused.status_code == 403
    assert "budget" in refused.json()["detail"]
    assert len(providers.sent) == 3


def test_keys_never_reach_the_browser_the_logs_or_the_investigation_files(tmp_path, caplog):
    caplog.set_level(logging.DEBUG)
    providers = FakeProviders(status={"api.meta.ai": 401})
    seen = []
    with TestClient(live_app(tmp_path, providers)) as client:
        failed_id, failed_events = run_live(client)
        seen.append(client.get(f"/api/investigations/{failed_id}").text)
        providers.status.clear()
        investigation_id, events = run_live(client)
        seen.append(client.get(f"/api/investigations/{investigation_id}").text)
        seen.append(client.get("/api/mode").text)
        seen.append(client.get(f"/api/investigations/{investigation_id}/package").content.decode("latin-1"))
    seen += [json.dumps(failed_events), json.dumps(events), caplog.text]
    seen += [path.read_bytes().decode("latin-1") for path in tmp_path.rglob("*") if path.is_file()]

    assert {s.authorization for s in providers.sent} == {f"Bearer {FAKE_KEYS['meta']}", f"Bearer {FAKE_KEYS['baseten']}"}
    assert failed_events[-1]["code"] == "provider_error"
    for key in FAKE_KEYS.values():
        assert not any(key in text for text in seen), "a provider key left the backend"
