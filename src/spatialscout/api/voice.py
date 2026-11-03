"""Push-to-talk questions: the browser posts a WAV, Muse Voice Transcribe returns text for the researcher to edit
and confirm. Transcribing starts nothing; only the confirmed question starts an investigation (ticket 08)."""

from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import FileResponse

from ..agent import utc_now
from ..contracts import Recording, Transcription
from ..gateway import GatewayError, LiveRunRefused, LiveSource, ModelGateway, ProviderError, ReplaySource, StoredResponseMissing
from ..gateway.audio import MAX_QUESTION_BYTES, ClipTooLong, ClipTooShort, InvalidAudio, check_question_wav
from ..gateway.gate import LiveGate
from ..settings import Settings

router = APIRouter()

VOICE_DIR = "voice"  # under the fixtures directory: the recorded clip and its stored transcription
SAMPLE_CLIP, VOICE_RECORDING = "question.wav", "recording.json"


def voice_dir(settings: Settings) -> Path:
    return settings.fixtures_dir / VOICE_DIR


def _problem(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def _replay_source(settings: Settings) -> ReplaySource:
    path = voice_dir(settings) / VOICE_RECORDING
    recording = Recording.model_validate_json(path.read_text(encoding="utf-8")) if path.is_file() else None
    if recording is None:
        raise _problem(404, StoredResponseMissing.code, "This server has no stored transcriptions. Type your question instead.")
    return ReplaySource(recording)


@router.post("/voice/transcribe")
async def transcribe(
    request: Request,
    run_mode: Literal["cached_tool_rerun", "live"] = "cached_tool_rerun",
    x_live_passcode: Annotated[str | None, Header()] = None,
    content_length: Annotated[int | None, Header()] = None,
) -> Transcription:
    """Transcribe a spoken question sent as the raw body (`audio/wav`: mono 16-bit PCM at 16 or 24 kHz, at most
    30 s), biased toward the dataset's panel genes. A cached tool rerun serves the stored transcription of a recorded
    clip and never calls a model; a live call needs the passcode in `X-Live-Passcode` and budget left today."""
    if content_length is not None and content_length > MAX_QUESTION_BYTES:
        raise _problem(413, "clip_too_long", "The recording is longer than a spoken question may be. Type your question instead.")
    wav = await request.body()
    try:
        clip = check_question_wav(wav)
    except ClipTooLong as error:
        raise _problem(413, "clip_too_long", f"{error} Type your question instead, or record a shorter one.") from None
    except (InvalidAudio, ClipTooShort) as error:
        raise _problem(400, "invalid_audio", str(error)) from None

    settings: Settings = request.app.state.settings
    live_gate: LiveGate = request.app.state.live_gate
    if run_mode == "live":
        try:
            source = LiveSource(live_gate.admit(x_live_passcode))
        except LiveRunRefused as refused:
            raise _problem(403, refused.code, str(refused)) from None
    else:
        source = _replay_source(settings)

    keywords = request.app.state.store.manifest(settings.dataset_id).panel
    gateway = ModelGateway(source, utc_now, run_mode=run_mode)
    try:
        transcript, record = await gateway.transcribe("question", wav, keywords)
    except StoredResponseMissing:
        raise _problem(
            404,
            StoredResponseMissing.code,
            "This server replays stored responses and has none for this recording, so new speech can't be transcribed. "
            "Type your question, or try the recorded clip.",
        ) from None
    except ProviderError as error:
        raise _problem(502, error.code, f"The transcription service failed: {error}. Type your question instead.") from None
    except GatewayError as error:
        raise _problem(502, error.code, f"Transcription failed: {error}. Type your question instead.") from None
    return Transcription(
        transcript=transcript.strip(),
        run_mode=run_mode,
        source=record.source,
        model=record.model,
        keywords=sorted(set(keywords)),
        audio_duration_ms=clip.duration_ms,
        latency_ms=record.latency_ms,
    )


@router.get("/voice/sample.wav", response_class=FileResponse)
async def sample_clip(request: Request) -> FileResponse:
    """The recorded clip whose transcription is stored, so a replaying server can still show voice end to end."""
    path = voice_dir(request.app.state.settings) / SAMPLE_CLIP
    if not path.is_file():
        raise _problem(404, "no_sample_clip", "This server has no recorded clip.")
    return FileResponse(path, media_type="audio/wav")
