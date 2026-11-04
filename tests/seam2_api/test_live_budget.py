"""Seam 2: the daily budget holds when live calls race, across servers sharing one spend directory.

Each fake call reserves and costs exactly $1.00 (fake_providers.FAKE_PRICES), so a $3.00 budget admits three.
"""

import dataclasses
import threading
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from spatialscout.api import create_app
from spatialscout.gateway import BudgetExhausted, SpendLedger
from spatialscout.settings import LiveSettings

from .conftest import RECORDED_QUESTION, make_settings
from .fake_providers import FAKE_PRICES, PASSCODE, FakeProviders, fake_keys
from .test_investigation_api import read_events


def server(tmp_path, name, providers, spend_dir, budget_usd):
    settings = dataclasses.replace(
        make_settings(tmp_path / name),
        live=LiveSettings(passcode=PASSCODE, daily_budget_usd=budget_usd, spend_dir=spend_dir),
    )
    return TestClient(create_app(settings, model_transport=providers.transport(), prices=FAKE_PRICES, api_keys=fake_keys()))


def test_parallel_live_runs_on_two_servers_never_spend_more_than_the_budget(tmp_path):
    providers = FakeProviders(delay_s=0.05)  # slow answers keep every reservation open while the others race
    spend_dir = tmp_path / "shared-spend"
    outcomes: list[str] = []
    lock = threading.Lock()

    def ask(client):
        response = client.post(
            "/api/investigations", json={"question": RECORDED_QUESTION, "run_mode": "live"}, headers={"X-Live-Passcode": PASSCODE}
        )
        if response.status_code == 403:
            outcome = "refused"
        else:
            outcome = read_events(client, response.json()["investigation_id"], until={"plan_proposed", "error"})[-1]["type"]
            if outcome == "error":
                outcome = read_events(client, response.json()["investigation_id"], until={"error"})[-1]["code"]
        with lock:
            outcomes.append(outcome)

    with server(tmp_path, "a", providers, spend_dir, 3.0) as first, server(tmp_path, "b", providers, spend_dir, 3.0) as second:
        threads = [threading.Thread(target=ask, args=(client,)) for client in [first, second] * 5]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    assert len(outcomes) == 10
    assert outcomes.count("plan_proposed") == 3
    assert set(outcomes) <= {"plan_proposed", "budget_exhausted", "refused"}
    assert len(providers.sent) == 3
    ledger = SpendLedger(spend_dir, 3.0, lambda: datetime.now(UTC))
    assert (ledger.spent_usd(), ledger.remaining_usd()) == (3.0, 0.0)


def test_racing_reservations_from_many_threads_never_exceed_the_budget(tmp_path):
    """Eight threads, each with its own ledger on the same directory (as separate servers would be), race to
    reserve one cent at a time against a one-dollar budget: exactly one hundred reservations succeed."""
    granted: list[str] = []
    lock = threading.Lock()

    def hammer():
        ledger = SpendLedger(tmp_path, 1.0, lambda: datetime.now(UTC))
        for _ in range(40):
            try:
                reservation = ledger.reserve(0.01, "race")
            except BudgetExhausted:
                continue
            with lock:
                granted.append(reservation)

    threads = [threading.Thread(target=hammer) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(granted) == 100
    assert SpendLedger(tmp_path, 1.0, lambda: datetime.now(UTC)).remaining_usd() < 0.01
