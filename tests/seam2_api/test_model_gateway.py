"""The model gateway's own public interface, on responses recorded live by `spatialscout smoke --run-mode live`.

SAM 3.1 and Muse Voice Transcribe have no HTTP route yet (tickets 07 and 08 add them), so these tests call the
gateway directly, with outbound network blocked by the seam-2 harness. Expected values come from the smoke
image's construction (two drawn discs) and the spoken question, not from the gateway's own code.
"""

import asyncio
import io
import json
import wave
from datetime import UTC, datetime

import numpy as np
import pytest

from spatialscout.contracts import Recording
from spatialscout.gateway import LiveClient, LiveSource, ModelGateway, ReplaySource, SpendLedger
from spatialscout.gateway.smoke import BOXES, DISCS, IMAGE_FILE, IMAGE_SIZE, run_smoke

from .conftest import REPO
from .fake_providers import FAKE_KEYS, FAKE_PRICES, fake_keys

SMOKE = REPO / "fixtures" / "smoke"
SPOKEN = "Does podocyte LRP2 survive nucleus only assignment"


def clock():
    return datetime.now(UTC)


def recording() -> Recording:
    return Recording.model_validate_json((SMOKE / "recording.json").read_text())


def stored_gateway(records=None) -> ModelGateway:
    return ModelGateway(ReplaySource(recording()), clock, run_mode="cached_tool_rerun", on_call=(records or []).append)


def test_the_smoke_check_replays_its_live_recording_with_no_network_and_identical_results():
    records = []
    results = asyncio.run(run_smoke(stored_gateway(records), SMOKE))

    assert [(r.provider, r.model, r.api) for r in results] == [
        ("meta", "muse-wonder-1.0", "chat_completions"),
        ("meta", "muse-wonder-1.0", "responses"),
        ("meta", "muse-spark-1.3", "chat_completions"),
        ("meta", "muse-spark-1.3", "responses"),
        ("baseten", "meta-models/muse-spark-open", "chat_completions"),
        ("fireworks", "accounts/fireworks/models/muse-spark-open", "chat_completions"),
        ("meta", "sam-3.1", "sam_segmentation"),
        ("meta", "muse-voice-transcribe-1.0", "asr_transcribe"),
    ]
    assert {r.source for r in results} == {"replay"}
    for result in results[:6]:  # every chat call answered the prompt's two numbers in the ClaimDraft contract
        cited = json.loads(result.output)["cited"]
        assert {name: number["value"] for name, number in cited.items()} == {"kept": 3, "total": 4}
    assert results[-1].output.rstrip("?.") == SPOKEN
    assert recording().info.origin == "live"
    # identical results: each output is exactly what the live call returned and the recording kept
    stored = {(c.request.provider, c.request.model, c.request.api): c.response.content for c in recording().calls}
    for result in results[:6]:
        assert json.loads(stored[(result.provider, result.model, result.api)]) == json.loads(result.output)


def test_sam_masks_are_box_local_crops_that_land_on_the_drawn_discs():
    width, height = IMAGE_SIZE
    png = (SMOKE / IMAGE_FILE).read_bytes()

    segmentation, record = asyncio.run(stored_gateway().segment_boxes("structure_masks", png, width, height, BOXES))

    assert record.source == "replay"
    assert [o.object_id for o in segmentation.objects] == [1, 2]
    rows, columns = np.mgrid[0:height, 0:width]
    for obj, (cx, cy, radius) in zip(segmentation.objects, DISCS, strict=True):
        assert obj.mask.shape == (obj.box.bottom - obj.box.top, obj.box.right - obj.box.left)  # a crop the size of its box
        disc = (columns - cx) ** 2 + (rows - cy) ** 2 <= radius**2
        placed = obj.place(width, height)
        assert (placed & disc).sum() == disc.sum()  # every pixel of the drawn disc is inside the mask
        assert (placed & disc).sum() / (placed | disc).sum() > 0.9


def test_a_different_image_misses_the_stored_sam_response():
    from spatialscout.gateway import StoredResponseMissing

    width, height = IMAGE_SIZE
    with pytest.raises(StoredResponseMissing):
        asyncio.run(stored_gateway().segment_boxes("structure_masks", b"\x89PNG other image", width, height, BOXES))


def test_transcription_returns_the_recorded_transcript():
    transcript, record = asyncio.run(stored_gateway().transcribe("question", (SMOKE / "question.wav").read_bytes()))

    assert transcript.rstrip("?.") == SPOKEN
    assert (record.provider, record.model, record.source) == ("meta", "muse-voice-transcribe-1.0", "replay")


def live_gateway(tmp_path, handler):
    import httpx2 as httpx

    client = LiveClient(fake_keys(), SpendLedger(tmp_path, 1.0, clock), FAKE_PRICES, transport=httpx.MockTransport(handler))
    return ModelGateway(LiveSource(client), clock, run_mode="live"), client


def test_a_live_transcription_uploads_the_wav_as_multipart_and_charges_its_duration(tmp_path):
    wav = (SMOKE / "question.wav").read_bytes()
    with wave.open(io.BytesIO(wav)) as reader:
        assert (reader.getnchannels(), reader.getsampwidth(), reader.getframerate()) == (1, 2, 16000)
    sent = []

    def handler(request):
        import httpx2 as httpx

        sent.append(request)
        return httpx.Response(200, json={"sessionId": "s", "transcript": SPOKEN + "?", "audioDurationMs": 4400, "turns": []})

    gateway, client = live_gateway(tmp_path, handler)
    transcript, record = asyncio.run(gateway.transcribe("question", wav))

    request = sent[0]
    assert (request.url.host, request.url.path) == ("api.meta.ai", "/v1/asr/transcribe")
    assert request.headers["authorization"] == f"Bearer {FAKE_KEYS['meta']}"
    assert request.headers["content-type"].startswith("multipart/form-data")
    body = request.content
    assert b'"model": "muse-voice-transcribe-1.0"' in body and b'"audioEncoding": "WAV"' in body
    assert wav in body
    assert transcript == SPOKEN + "?"
    assert record.estimated_cost_usd == pytest.approx(4 * 0.001)  # 4 whole seconds at the fake $0.001 per second


@pytest.mark.parametrize("without_text_done", [False, True], ids=["as-recorded", "without-output_text.done"])
def test_a_live_sam_call_streams_the_box_prompt_and_parses_the_recorded_events(tmp_path, without_text_done):
    """`without-output_text.done` replays the stream as Meta's cookbook describes it, before the API sent that
    event: the gateway synthesises it from `response.content_part.done`."""
    stored = next(c for c in recording().calls if c.request.api == "sam_segmentation")
    events = [e for e in stored.response.events if not (without_text_done and e["type"] == "response.output_text.done")]
    stream = "".join(f"data: {json.dumps(event)}\n\n" for event in events) + "data: [DONE]\n\n"
    sent = []

    def handler(request):
        import httpx2 as httpx

        sent.append(json.loads(request.content))
        return httpx.Response(200, text=stream, headers={"content-type": "text/event-stream"})

    gateway, _ = live_gateway(tmp_path, handler)
    width, height = IMAGE_SIZE
    segmentation, record = asyncio.run(gateway.segment_boxes("structure_masks", (SMOKE / IMAGE_FILE).read_bytes(), width, height, BOXES))

    body = sent[0]
    assert (body["model"], body["stream"]) == ("sam-3.1", True)
    prompt, image = body["input"][0]["content"]
    assert prompt["text"].startswith("<0f>1<|box;") and ",2<|box;" in prompt["text"]
    assert image["image_url"].startswith("data:image/png;base64,")
    assert [int(o.mask.sum()) for o in segmentation.objects] == [478, 267]
    assert (record.source, record.estimated_cost_usd) == ("live", 0.01)
