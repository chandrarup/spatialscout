"""Stored model responses: recordings on disk and the source that serves them without any network call."""

from pathlib import Path

from ..contracts import ModelRequest, ModelResponse, Recording, ReplayInfo
from .gateway import StoredResponseMissing, cache_key


class StaleRecording(ValueError):
    """A recording whose stored cache key no longer matches its own request: regenerate it."""


class ReplaySource:
    """Serves a recording's responses by cache key. It never calls a model."""

    kind = "replay"

    def __init__(self, recording: Recording) -> None:
        self.recording_id = recording.info.recording_id
        self._responses: dict[str, ModelResponse] = {}
        for call in recording.calls:
            if cache_key(call.request, call.inputs) != call.cache_key:
                raise StaleRecording(f"recording {self.recording_id}: the stored key of its {call.purpose} call is stale")
            self._responses[call.cache_key] = call.response

    async def respond(self, key: str, request: ModelRequest) -> ModelResponse:
        response = self._responses.get(key)
        if response is None:
            raise StoredResponseMissing(
                f"no stored {request.model} response matches this request (cache key {key[:12]}). Either the question "
                "has no recording, or a tool, artifact or prompt changed since it was recorded."
            )
        return response


def normalise_question(question: str) -> str:
    """Questions match recordings after trimming and collapsing whitespace; wording and case must agree."""
    return " ".join(question.split())


class RecordingLibrary:
    """Every recording under a directory, as `<recording_id>/recording.json`."""

    def __init__(self, recordings_dir: Path) -> None:
        paths = sorted(Path(recordings_dir).glob("*/recording.json"))
        self._recordings = [Recording.model_validate_json(p.read_text(encoding="utf-8")) for p in paths]

    def infos(self) -> list[ReplayInfo]:
        return [r.info for r in self._recordings]

    def for_question(self, question: str) -> Recording | None:
        wanted = normalise_question(question)
        return next((r for r in self._recordings if normalise_question(r.info.question) == wanted), None)
