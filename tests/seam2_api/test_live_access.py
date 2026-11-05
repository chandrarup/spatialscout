"""Seam 2: the three ways a live run reaches the models — the owner's passcode, the open trial on the server's keys,
and bring-your-own-key — with fake providers behind the model transport. A visitor's keys reach only that visitor's
provider calls and never a file the investigation writes."""

import dataclasses
import json

from fastapi.testclient import TestClient

from spatialscout.api import create_app
from spatialscout.gateway import ApiKeys
from spatialscout.settings import LiveSettings

from .conftest import RECORDED_QUESTION, make_settings
from .fake_providers import FAKE_PRICES, FakeProviders
from .test_investigation_api import approve, read_events

VISITOR = {"meta": "LLM_visitor-meta-key-1234", "baseten": "bt-visitor-baseten-key-5678"}
SERVER = {"meta": "LLM_server-meta-key-0000", "baseten": "bt-server-baseten-key-0000"}


def app(tmp_path, providers: FakeProviders, trial_usd: float | None = None):
    settings = dataclasses.replace(make_settings(tmp_path), live=LiveSettings(spend_dir=tmp_path / "spend", trial_daily_usd=trial_usd))
    return create_app(settings, model_transport=providers.transport(), prices=FAKE_PRICES, api_keys=ApiKeys(SERVER))  # type: ignore[arg-type]


def start(client, headers):
    return client.post("/api/investigations", json={"question": RECORDED_QUESTION, "run_mode": "live"}, headers=headers)


def run(client, headers):
    response = start(client, headers)
    assert response.status_code == 201, response.text
    investigation_id = response.json()["investigation_id"]
    read_events(client, investigation_id, until={"plan_proposed", "error"})
    approve(client, investigation_id)
    return investigation_id, read_events(client, investigation_id)


def test_the_mode_lists_the_access_this_server_offers(tmp_path):
    with TestClient(app(tmp_path, FakeProviders())) as client:
        closed = client.get("/api/mode").json()
    with TestClient(app(tmp_path, FakeProviders(), trial_usd=2.0)) as client:
        open_ = client.get("/api/mode").json()

    assert (closed["live_access"], closed["trial_remaining_usd"]) == (["byok"], None)
    assert (open_["live_access"], open_["trial_remaining_usd"]) == (["trial", "byok"], 2.0)


def test_a_trial_run_needs_no_passcode_and_spends_the_server_keys(tmp_path):
    providers = FakeProviders()
    with TestClient(app(tmp_path, providers, trial_usd=50.0)) as client:
        _, events = run(client, {"X-Live-Access": "trial"})

    assert events[-1]["type"] == "package_ready"
    assert providers.sent and {s.authorization for s in providers.sent} <= {f"Bearer {v}" for v in SERVER.values()}


def test_a_closed_trial_refuses_and_creates_nothing(tmp_path):
    providers = FakeProviders()
    with TestClient(app(tmp_path, providers)) as client:
        refused = start(client, {"X-Live-Access": "trial"})

    assert refused.status_code == 403
    assert providers.sent == [] and not list((tmp_path / "investigations").glob("inv-*"))


def test_bring_your_own_key_uses_only_the_visitors_keys_and_never_writes_them(tmp_path):
    providers = FakeProviders()
    headers = {"X-Live-Access": "byok", "X-Provider-Keys": json.dumps(VISITOR), "X-Spend-Cap-Usd": "5"}
    with TestClient(app(tmp_path, providers)) as client:
        investigation_id, events = run(client, headers)

    assert events[-1]["type"] == "package_ready"
    assert providers.sent and {s.authorization for s in providers.sent} <= {f"Bearer {v}" for v in VISITOR.values()}
    written = b"".join(p.read_bytes() for p in (tmp_path / "investigations" / investigation_id).rglob("*") if p.is_file())
    assert not any(key.encode() in written for key in VISITOR.values())
    assert b'"live_access": "byok"' in written or b'"live_access":"byok"' in written


def test_bring_your_own_key_refuses_missing_keys_and_an_oversized_cap(tmp_path):
    providers = FakeProviders()
    with TestClient(app(tmp_path, providers)) as client:
        no_keys = start(client, {"X-Live-Access": "byok"})
        no_meta = start(client, {"X-Live-Access": "byok", "X-Provider-Keys": json.dumps({"baseten": "bt-x"})})
        no_open = start(client, {"X-Live-Access": "byok", "X-Provider-Keys": json.dumps({"meta": "LLM_x"})})
        too_much = start(client, {"X-Live-Access": "byok", "X-Provider-Keys": json.dumps(VISITOR), "X-Spend-Cap-Usd": "500"})

    assert [r.status_code for r in (no_keys, no_meta, no_open, too_much)] == [403, 403, 403, 403]
    assert "Meta" in no_meta.json()["detail"] and "Baseten or Fireworks" in no_open.json()["detail"]
    assert providers.sent == []
