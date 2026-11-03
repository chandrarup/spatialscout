"""Stored model responses: recordings on disk and the source that serves them without any network call."""

from pathlib import Path

from ..contracts import ModelRequest, ModelResponse, RecordedCall, Recording, ReplayInfo
from .errors import StoredResponseMissing
from .gateway import cache_key


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

    async def respond(self, key: str, request: ModelRequest, media: bytes | None = None) -> tuple[ModelResponse, float | None]:
        response = self._responses.get(key)
        if response is None:
            raise StoredResponseMissing(
                f"no stored {request.model} response matches this request (cache key {key[:12]}). Either the question "
                "has no recording, or a tool, artifact or prompt changed since it was recorded."
            )
        return response, None


def normalise_question(question: str) -> str:
    """Questions match recordings after trimming and collapsing whitespace; wording and case must agree."""
    return " ".join(question.split())


RECORDED_INVESTIGATION_DIR = "investigation"


class RecordingLibrary:
    """Every recording under a directory, as `<recording_id>/recording.json`: the stored model responses a
    cached tool rerun serves, and optionally `<recording_id>/investigation/`, a whole recorded investigation
    (state.json, events.jsonl, audit_log.jsonl, package.zip) that immutable replay streams verbatim."""

    def __init__(self, recordings_dir: Path) -> None:
        paths = sorted(Path(recordings_dir).glob("*/recording.json"))
        self._recordings = [Recording.model_validate_json(p.read_text(encoding="utf-8")) for p in paths]
        self._investigation_dirs: dict[str, Path] = {}
        for path in paths:
            directory = path.parent / RECORDED_INVESTIGATION_DIR
            if (directory / "state.json").is_file():
                self._investigation_dirs[path.parent.name] = directory

    def infos(self) -> list[ReplayInfo]:
        return [r.info for r in self._recordings]

    def for_question(self, question: str) -> Recording | None:
        wanted = normalise_question(question)
        return next((r for r in self._recordings if normalise_question(r.info.question) == wanted), None)

    def recorded_investigation(self, question: str) -> tuple[Path, ReplayInfo] | None:
        """The recorded investigation that answers this question, for immutable replay."""
        recording = self.for_question(question)
        if recording is None or recording.info.recording_id not in self._investigation_dirs:
            return None
        return self._investigation_dirs[recording.info.recording_id], recording.info

    def recorded_investigation_by_id(self, investigation_id: str) -> tuple[Path, ReplayInfo] | None:
        for recording in self._recordings:
            directory = self._investigation_dirs.get(recording.info.recording_id)
            if directory is not None and _recorded_id(directory) == investigation_id:
                return directory, recording.info
        return None

    def has_recorded_investigations(self) -> bool:
        return bool(self._investigation_dirs)


def _recorded_id(directory: Path) -> str | None:
    import json

    return json.loads((directory / "state.json").read_text(encoding="utf-8")).get("investigation_id")


class RecordingWriter:
    """Writes every live response of a run to a recording, rewritten after each call, so a cached tool rerun
    can replay the run. The same cache key keeps its latest response."""

    def __init__(self, path: Path, info: ReplayInfo) -> None:
        self._path = Path(path)
        self._info = info
        self._calls: dict[str, RecordedCall] = {}

    def add(self, call: RecordedCall) -> None:
        self._calls[call.cache_key] = call
        recording = Recording(info=self._info, calls=list(self._calls.values()))
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(".tmp")
        temporary.write_text(recording.model_dump_json(indent=1) + "\n", encoding="utf-8")
        temporary.replace(self._path)
