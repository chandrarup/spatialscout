"""A spoken question's transcript, returned for the researcher to edit and confirm (ticket 08)."""

from typing import Literal

from pydantic import Field

from .base import Contract, RunMode


class Transcription(Contract):
    """What Muse Voice Transcribe heard. Nothing runs on it until the researcher confirms the edited text."""

    transcript: str
    run_mode: RunMode = Field(description="`cached_tool_rerun` serves a stored response; `live` made a fresh call.")
    source: Literal["live", "replay", "cache"]
    model: str
    keywords: list[str] = Field(description="The panel genes recognition was biased toward.")
    audio_duration_ms: int = Field(description="The clip's length, read from its WAV header.")
    latency_ms: int
