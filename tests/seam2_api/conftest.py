"""Seam 2 harness: the FastAPI app through its test client, with the model gateway on recorded responses.

Every test runs with outbound network connections blocked, so a passing test proves the investigation
ran from the recorded-response fixture alone.
"""

import socket
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from spatialscout.api import create_app
from spatialscout.settings import Settings

REPO = Path(__file__).resolve().parents[2]
RECORDED_QUESTION = "Does podocyte LRP2 in the synthetic section survive nucleus-only assignment?"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Refuse every outbound connection. Only `connect` is patched: the event loop needs local sockets."""

    def refuse(self, address, *args, **kwargs):
        raise AssertionError(f"network access attempted: {address!r}")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse)


@pytest.fixture
def client(tmp_path):
    settings = Settings(
        fixtures_dir=REPO / "fixtures",
        recordings_dir=REPO / "fixtures" / "recordings",
        investigations_dir=tmp_path / "investigations",
        web_dist=None,
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client
