"""The model gateway: one interface for every model call, whatever the source of the response.

Ticket 01 has one source, stored responses (`ReplaySource`), which serves `cached_tool_rerun`. Ticket 03
adds the live source, the immutable-replay source, the budget gate, failover and telemetry behind the
same `complete_json` call.
"""

import time
from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Literal, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from ..contracts import CacheInput, ModelCallRecord, ModelRequest, ModelResponse, canonical_json, new_id, sha256_hex

Output = TypeVar("Output", bound=BaseModel)


class GatewayError(Exception):
    """A model call that produced no usable response. `code` names the failure in events and the audit log."""

    code = "model_gateway_error"

    def __init__(self, message: str, record: ModelCallRecord | None = None) -> None:
        super().__init__(message)
        self.record = record


class StoredResponseMissing(GatewayError):
    """No stored response matches the request's cache key, and this source never calls a model."""

    code = "replay_miss"


class ModelOutputInvalid(GatewayError):
    code = "model_output_invalid"


class ResponseSource(Protocol):
    kind: Literal["live", "replay", "cache"]
    recording_id: str | None

    async def respond(self, key: str, request: ModelRequest) -> ModelResponse: ...


def cache_key(request: ModelRequest, inputs: Sequence[CacheInput]) -> str:
    """The content address of a model call: the full request (provider, model, messages, response schema)
    plus the version and checksum of every computed input it was built from."""
    payload = {"request": request.model_dump(mode="json"), "inputs": [i.model_dump(mode="json") for i in inputs]}
    return sha256_hex(canonical_json(payload))


class ModelGateway:
    def __init__(self, source: ResponseSource, clock: Callable[[], datetime]) -> None:
        self._source = source
        self._clock = clock

    async def complete_json(
        self, purpose: str, request: ModelRequest, inputs: Sequence[CacheInput], output_model: type[Output]
    ) -> tuple[Output, ModelCallRecord]:
        """Get a structured response and validate it locally against `output_model`."""
        key = cache_key(request, inputs)
        started_at, started = self._clock(), time.perf_counter()
        response = await self._source.respond(key, request)
        record = ModelCallRecord(
            call_id=new_id("mcl"),
            purpose=purpose,
            provider=request.provider,
            model=request.model,
            cache_key=key,
            source=self._source.kind,
            recording_id=self._source.recording_id,
            started_at=started_at,
            latency_ms=round((time.perf_counter() - started) * 1000),
            finish_reason=response.finish_reason,
            usage=response.usage,
        )
        try:
            return output_model.model_validate_json(response.content), record
        except ValidationError as error:
            raise ModelOutputInvalid(
                f"the {purpose} response does not match {output_model.__name__} ({error.error_count()} errors)", record
            ) from error
