"""Seam 2: a spoken question through `POST /api/voice/transcribe`, with outbound network blocked.

The recorded clip is `fixtures/voice/question.wav` (the smoke clip). Its stored response was recorded live by
`scripts/record_voice_sample.py`, with the dataset's panel genes sent as keywords. Expected transcripts come from
what was spoken, not from the gateway's code.
"""

import dataclasses
import io
import json
import wave

import httpx2 as httpx
from fastapi.testclient import TestClient

from spatialscout.api import create_app
from spatialscout.settings import LiveSettings

from .conftest import REPO, make_settings
from .fake_providers import FAKE_KEYS, FAKE_PRICES, PASSCODE, fake_keys

VOICE = REPO / "fixtures" / "voice"
SPOKEN = "does podocyte lrp2 survive nucleus only assignment"
WAV = {"content-type": "audio/wav"}


def words(text: str) -> str:
    return " ".join("".join(c for c in text.lower() if c.isalnum() or c.isspace() or c == "-").replace("-", " ").split())


def clip() -> bytes:
    return (VOICE / "question.wav").read_bytes()


def test_the_recorded_clip_transcribes_under_a_cached_tool_rerun_with_no_network(client):
    response = client.post("/api/voice/transcribe", content=clip(), headers=WAV)

    assert response.status_code == 200, response.text
    body = response.json()
    assert words(body["transcript"]) == SPOKEN
    assert (body["run_mode"], body["source"], body["model"]) == ("cached_tool_rerun", "replay", "muse-voice-transcribe-1.0")
    assert "LRP2" in body["keywords"] and "NPHS1" in body["keywords"]  # biased toward the synthetic panel


def tone_wav(seconds: float, rate: int = 16000, channels: int = 1) -> bytes:
    """A hand-built 16-bit WAV of the given shape (a sawtooth, so it is not silence)."""
    frame = lambda i: (i * 37 % 2000 - 1000).to_bytes(2, "little", signed=True) * channels  # noqa: E731
    out = io.BytesIO()
    with wave.open(out, "wb") as writer:
        writer.setnchannels(channels)
        writer.setsampwidth(2)
        writer.setframerate(rate)
        writer.writeframes(b"".join(frame(i) for i in range(int(seconds * rate))))
    return out.getvalue()


def test_transcribing_starts_no_investigation(client, tmp_path):
    assert client.post("/api/voice/transcribe", content=clip(), headers=WAV).status_code == 200

    investigations = tmp_path / "investigations"
    assert not investigations.exists() or list(investigations.iterdir()) == []


def test_new_speech_under_a_cached_tool_rerun_misses_with_a_message_that_says_to_type(client):
    response = client.post("/api/voice/transcribe", content=tone_wav(2.0), headers=WAV)

    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["code"] == "replay_miss"
    assert "Type your question" in detail["message"]


def test_audio_the_transcriber_does_not_accept_is_refused_before_any_model_call(client):
    stereo = client.post("/api/voice/transcribe", content=tone_wav(2.0, channels=2), headers=WAV)
    cd_rate = client.post("/api/voice/transcribe", content=tone_wav(2.0, rate=44100), headers=WAV)
    not_wav = client.post("/api/voice/transcribe", content=b"OggS not a wav", headers=WAV)
    a_tap = client.post("/api/voice/transcribe", content=tone_wav(0.1), headers=WAV)

    refused = (stereo, cd_rate, not_wav, a_tap)
    assert [r.status_code for r in refused] == [400, 400, 400, 400]
    assert {r.json()["detail"]["code"] for r in refused} == {"invalid_audio"}
    assert "mono 16-bit" in stereo.json()["detail"]["message"]


def test_a_clip_longer_than_thirty_seconds_is_refused_as_too_long(client):
    response = client.post("/api/voice/transcribe", content=tone_wav(31.0), headers=WAV)

    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "clip_too_long"


def live_voice_app(tmp_path, sent: list):
    """The app with live runs enabled and a fake Muse Voice Transcribe behind the model transport."""

    def handler(request):
        sent.append(request)
        return httpx.Response(200, json={"sessionId": "s", "transcript": "Is NPHS1 kept in podocytes?", "audioDurationMs": 2000, "turns": []})

    settings = dataclasses.replace(
        make_settings(tmp_path), live=LiveSettings(passcode=PASSCODE, daily_budget_usd=1.0, spend_dir=tmp_path / "spend")
    )
    return create_app(settings, model_transport=httpx.MockTransport(handler), prices=FAKE_PRICES, api_keys=fake_keys())


def test_a_live_transcription_without_the_passcode_is_refused_and_calls_no_model(tmp_path):
    sent = []
    with TestClient(live_voice_app(tmp_path, sent)) as live_client:
        missing = live_client.post("/api/voice/transcribe?run_mode=live", content=tone_wav(2.0), headers=WAV)
        wrong = live_client.post("/api/voice/transcribe?run_mode=live", content=tone_wav(2.0), headers={**WAV, "X-Live-Passcode": "guess"})

    assert (missing.status_code, wrong.status_code) == (403, 403)
    assert sent == []


def test_a_live_transcription_with_the_passcode_sends_the_panel_genes_as_keywords(tmp_path):
    sent = []
    with TestClient(live_voice_app(tmp_path, sent)) as live_client:
        response = live_client.post(
            "/api/voice/transcribe?run_mode=live", content=tone_wav(2.0), headers={**WAV, "X-Live-Passcode": PASSCODE}
        )

    assert response.status_code == 200, response.text
    assert (response.json()["transcript"], response.json()["run_mode"], response.json()["source"]) == (
        "Is NPHS1 kept in podocytes?",
        "live",
        "live",
    )
    assert response.json()["audio_duration_ms"] == 2000
    (request,) = sent
    assert request.url.path == "/v1/asr/transcribe"
    part = request.content.split(b"\r\n\r\n", 1)[1].split(b"\r\n--", 1)[0]
    assert json.loads(part)["keywords"] == ["CD3D", "CUBN", "LRP2", "NPHS1", "PDGFRB", "PECAM1", "UMOD"]  # the synthetic panel


def test_a_failing_transcription_service_falls_back_with_a_message(tmp_path):
    def handler(request):
        return httpx.Response(503, json={"error": {"code": "unavailable", "type": "server_error", "message": "down"}})

    settings = dataclasses.replace(
        make_settings(tmp_path), live=LiveSettings(passcode=PASSCODE, daily_budget_usd=1.0, spend_dir=tmp_path / "spend")
    )
    app = create_app(settings, model_transport=httpx.MockTransport(handler), prices=FAKE_PRICES, api_keys=fake_keys())
    with TestClient(app) as live_client:
        response = live_client.post(
            "/api/voice/transcribe?run_mode=live", content=tone_wav(2.0), headers={**WAV, "X-Live-Passcode": PASSCODE}
        )

    assert response.status_code == 502
    assert "Type your question" in response.json()["detail"]["message"]
    assert FAKE_KEYS["meta"] not in response.text


def test_the_recorded_clip_is_served_for_a_replaying_demo(client):
    response = client.get("/api/voice/sample.wav")

    assert response.status_code == 200
    assert response.content == clip()
