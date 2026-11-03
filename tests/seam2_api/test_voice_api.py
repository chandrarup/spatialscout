"""Seam 2: a spoken question through `POST /api/voice/transcribe`, with outbound network blocked.

The recorded clip is `fixtures/voice/question.wav` (the smoke clip). Its stored response was recorded live by
`scripts/record_voice_sample.py`, with the dataset's panel genes sent as keywords. Expected transcripts come from
what was spoken, not from the gateway's code.
"""

import io
import wave

from .conftest import REPO

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
