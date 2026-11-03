"""The model gateway: one interface for every model call, whatever the source of the response.

Sources (ADR-0003):
- `ReplaySource` serves stored responses by cache key and never calls a model (`cached_tool_rerun`);
- `LiveSource` makes fresh calls under the passcode-gated daily budget (`live`), and the gateway records each
  one so a later cached tool rerun replays it.
(`immutable_replay` never reaches the gateway: it streams recorded events verbatim.)

Every call, successful or not, produces a `ModelCallRecord` handed to `on_call`, which the orchestrator writes
to the audit log and streams as a telemetry event. Structured outputs are validated locally against their
Pydantic model, with one bounded repair attempt.
"""

import hashlib
import re
import time
from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Literal, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from ..contracts import (
    CacheInput,
    ChatMessage,
    ModelCallRecord,
    ModelRequest,
    ModelResponse,
    RecordedCall,
    RunMode,
    canonical_json,
    new_id,
    sha256_hex,
)
from .errors import GatewayError, ModelOutputInvalid, ModelOutputTruncated, StoredResponseMissing
from .sam import Box, Segmentation, box_prompt, parse_segmentation

Output = TypeVar("Output", bound=BaseModel)

SAM_MODEL = "sam-3.1"
TRANSCRIBE_MODEL = "muse-voice-transcribe-1.0"

__all__ = ["GatewayError", "ModelGateway", "ModelOutputInvalid", "ModelOutputTruncated", "ResponseSource", "StoredResponseMissing", "cache_key"]


class ResponseSource(Protocol):
    kind: Literal["live", "replay", "cache"]
    recording_id: str | None

    async def respond(self, key: str, request: ModelRequest, media: bytes | None = None) -> tuple[ModelResponse, float | None]:
        """The response, and the spend it was charged (None when nothing was spent)."""
        ...


class CallRecorder(Protocol):
    def add(self, call: RecordedCall) -> None: ...


def cache_key(request: ModelRequest, inputs: Sequence[CacheInput]) -> str:
    """The content address of a model call: the full request (provider, model, messages, response schema,
    endpoint) plus the version and checksum of every computed input it was built from, including any image
    or audio sent with it."""
    dumped = request.model_dump(mode="json")
    if not dumped.get("keywords"):
        dumped.pop("keywords", None)
    payload = {"request": dumped, "inputs": [i.model_dump(mode="json") for i in inputs]}
    return sha256_hex(canonical_json(payload))


def media_input(name: str, media: bytes) -> CacheInput:
    return CacheInput(name=name, version="bytes", sha256=hashlib.sha256(media).hexdigest())


class ModelGateway:
    def __init__(
        self,
        source: ResponseSource,
        clock: Callable[[], datetime],
        *,
        run_mode: RunMode | None = None,
        on_call: Callable[[ModelCallRecord], None] | None = None,
        recorder: CallRecorder | None = None,
    ) -> None:
        self._source = source
        self._clock = clock
        self._run_mode = run_mode
        self._on_call = on_call or (lambda record: None)
        self._recorder = recorder

    async def complete_json(
        self, purpose: str, request: ModelRequest, inputs: Sequence[CacheInput], output_model: type[Output]
    ) -> tuple[Output, ModelCallRecord]:
        """A structured response, validated locally against `output_model`. One invalid response gets exactly
        one repair request (itself cached and recorded); a second invalid response raises ModelOutputInvalid."""
        response, record = await self._call(purpose, request, inputs)
        try:
            return output_model.model_validate_json(json_text(response.content)), record
        except ValidationError as error:
            first_error = error
        repair = repair_request(request, response.content, first_error)
        response, record = await self._call(f"{purpose}_repair", repair, inputs)
        try:
            return output_model.model_validate_json(json_text(response.content)), record
        except ValidationError as error:
            raise ModelOutputInvalid(
                f"the {purpose} response does not match {output_model.__name__}, even after one repair "
                f"({error.error_count()} errors)",
                record,
            ) from error

    async def segment_boxes(
        self, purpose: str, png: bytes, width: int, height: int, boxes: Sequence[Box], inputs: Sequence[CacheInput] = ()
    ) -> tuple[Segmentation, ModelCallRecord]:
        """SAM 3.1 masks for up to 16 box prompts on a PNG image. Masks are box-local crops (see `sam.py`)."""
        request = ModelRequest(
            provider="meta",
            model=SAM_MODEL,
            api="sam_segmentation",
            messages=[ChatMessage(role="user", content=box_prompt(width, height, boxes))],
        )
        response, record = await self._call(purpose, request, [*inputs, media_input("image/png", png)], png)
        return await parse_segmentation(response.events or [], width, height), record

    async def transcribe(self, purpose: str, wav: bytes, keywords: Sequence[str] = ()) -> tuple[str, ModelCallRecord]:
        """Muse Voice Transcribe on a WAV file (mono 16-bit PCM at 16 or 24 kHz), biased toward `keywords` (sorted
        and de-duplicated, so the cache key does not depend on their order). Returns the transcript."""
        request = ModelRequest(
            provider="meta",
            model=TRANSCRIBE_MODEL,
            api="asr_transcribe",
            messages=[ChatMessage(role="user", content="Transcribe the attached WAV audio.")],
            keywords=sorted(set(keywords)),
        )
        response, record = await self._call(purpose, request, [media_input("audio/wav", wav)], wav)
        return response.content, record

    async def _call(
        self, purpose: str, request: ModelRequest, inputs: Sequence[CacheInput], media: bytes | None = None
    ) -> tuple[ModelResponse, ModelCallRecord]:
        key = cache_key(request, inputs)
        started_at, started = self._clock(), time.perf_counter()
        record = ModelCallRecord(
            call_id=new_id("mcl"),
            purpose=purpose,
            provider=request.provider,
            model=request.model,
            cache_key=key,
            source=self._source.kind,
            recording_id=self._source.recording_id,
            started_at=started_at,
            latency_ms=0,
            finish_reason="error",
            run_mode=self._run_mode,
        )
        try:
            response, cost = await self._source.respond(key, request, media)
        except GatewayError as error:
            error.record = record.model_copy(
                update={"latency_ms": _elapsed_ms(started), "error_code": error.code}
            )
            self._on_call(error.record)
            raise
        latency_ms = _elapsed_ms(started)
        served_by = response.served_by or request.provider
        record = record.model_copy(
            update={
                "latency_ms": latency_ms,
                "finish_reason": response.finish_reason,
                "usage": response.usage,
                "estimated_cost_usd": cost,
                "served_by": served_by,
                "failover_from": request.provider if served_by != request.provider else None,
            }
        )
        if self._recorder is not None and self._source.kind == "live":
            self._recorder.add(
                RecordedCall(purpose=purpose, cache_key=key, request=request, inputs=list(inputs), response=response, latency_ms=latency_ms)
            )
        if not response.content.strip() and response.finish_reason == "length":
            record = record.model_copy(update={"error_code": ModelOutputTruncated.code})
            self._on_call(record)
            raise ModelOutputTruncated(
                f"the {purpose} call to {request.model} returned no content: it spent its {request.max_tokens}-token cap "
                "reasoning (finish reason 'length')",
                record,
            )
        self._on_call(record)
        return response, record


def json_text(content: str) -> str:
    """The JSON object in a response, without the Markdown code fence some models wrap it in."""
    fenced = re.fullmatch(r"\s*```(?:json)?\s*(.*?)\s*```\s*", content, flags=re.DOTALL)
    return fenced.group(1) if fenced else content


def repair_request(request: ModelRequest, invalid: str, error: ValidationError) -> ModelRequest:
    """The one repair attempt: the original conversation, the invalid answer, and what was wrong with it.
    Built only from the request and the response, so it has a stable cache key of its own."""
    problems = [f"{'.'.join(str(p) for p in e['loc']) or '(root)'}: {e['msg']}" for e in error.errors(include_url=False)[:10]]
    feedback = (
        "Your previous answer does not match the response schema. Problems:\n- "
        + "\n- ".join(problems)
        + "\nRespond again with only the corrected JSON object."
    )
    return request.model_copy(
        update={
            "messages": [
                *request.messages,
                ChatMessage(role="assistant", content=invalid[:20000]),
                ChatMessage(role="user", content=feedback),
            ]
        }
    )


def _elapsed_ms(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)
