"""Checks a spoken question's WAV before it reaches Muse Voice Transcribe, which accepts only a RIFF/WAVE file of
mono 16-bit integer PCM at 16 or 24 kHz (docs/research/meta-platform.md, section 4)."""

import wave
from dataclasses import dataclass
from io import BytesIO

ACCEPTED_RATES_HZ = (16000, 24000)
MAX_QUESTION_SECONDS = 30.0
MIN_QUESTION_SECONDS = 0.3
# The largest valid question clip: 30 s of 16-bit mono at 24 kHz, plus room for the header.
MAX_QUESTION_BYTES = int(MAX_QUESTION_SECONDS * 24000 * 2) + 4096


class InvalidAudio(ValueError):
    """Not a WAV the transcriber accepts: wrong container, channels, sample width or rate."""


class ClipTooLong(ValueError):
    """Longer than a spoken question may be."""


class ClipTooShort(ValueError):
    """Too short to hold a question: usually a tap on the record button."""


@dataclass(frozen=True)
class WavClip:
    sample_rate_hz: int
    duration_ms: int


def check_question_wav(wav: bytes) -> WavClip:
    """The clip's rate and length, or InvalidAudio, ClipTooLong or ClipTooShort."""
    if len(wav) > MAX_QUESTION_BYTES:
        raise ClipTooLong(f"The recording is longer than {MAX_QUESTION_SECONDS:.0f} seconds.")
    try:
        with wave.open(BytesIO(wav)) as reader:
            channels, width, rate, frames = reader.getnchannels(), reader.getsampwidth(), reader.getframerate(), reader.getnframes()
    except (wave.Error, EOFError) as error:
        raise InvalidAudio(f"The recording is not a readable WAV file ({error}).") from None
    if channels != 1 or width != 2 or rate not in ACCEPTED_RATES_HZ:
        raise InvalidAudio(
            f"The recording is {channels}-channel, {8 * width}-bit at {rate} Hz; the transcriber needs mono 16-bit PCM "
            "at 16 or 24 kHz."
        )
    seconds = frames / rate
    if seconds > MAX_QUESTION_SECONDS:
        raise ClipTooLong(f"The recording is {seconds:.0f} seconds; a spoken question may be at most {MAX_QUESTION_SECONDS:.0f}.")
    if seconds < MIN_QUESTION_SECONDS:
        raise ClipTooShort("The recording is too short to hold a question. Hold the button while you speak.")
    return WavClip(rate, round(seconds * 1000))
