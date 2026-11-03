"""The live source: fresh calls to Meta, Baseten and Fireworks, each paid for from the daily budget.

Request shapes follow the live probes of Nov 2 (`docs/research/provider-smoke-tests.md`):
- chat completions: `max_tokens`, `reasoning_effort`, `response_format: {type: json_schema, ...}`
- responses (Meta): `max_output_tokens`, `reasoning: {effort}`, `text: {format: {type: json_schema, ...}}`;
  a capped answer comes back `status: incomplete`, reported here as finish reason "length"
- SAM 3.1: a streamed responses call whose events are kept verbatim for the parser
- Muse Voice Transcribe: multipart `request` JSON plus the WAV `audio` part

Every model here reasons before answering, so requests always carry a generous token cap (`ModelRequest`
refuses less than 2,000) and `reasoning_effort` "low" by default.
"""

import base64
import json
import wave
from dataclasses import dataclass
from io import BytesIO
from typing import Any

import httpx2 as httpx

from ..contracts import ModelRequest, ModelResponse, Provider, TokenUsage
from .budget import SpendLedger
from .errors import GatewayError, ProviderError
from .providers import BASE_URLS, FAILOVER, ApiKeys, PriceBook

RESPONSE_SCHEMA_NAME = "response"
ASR_MODES = {"muse-voice-transcribe-1.0": "PUSH_TO_TALK"}


@dataclass
class LiveResult:
    response: ModelResponse
    cost_usd: float
    served_by: Provider
    failover_from: Provider | None


class LiveClient:
    """Makes live calls. Owns the HTTP client, the keys, the prices and the budget ledger."""

    def __init__(
        self,
        keys: ApiKeys,
        ledger: SpendLedger,
        prices: PriceBook,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout_s: float = 120.0,
    ) -> None:
        self._keys = keys
        self._ledger = ledger
        self._prices = prices
        self._http = httpx.AsyncClient(transport=transport, timeout=timeout_s)

    @property
    def ledger(self) -> SpendLedger:
        return self._ledger

    async def aclose(self) -> None:
        await self._http.aclose()

    async def call(self, request: ModelRequest, media: bytes | None = None) -> LiveResult:
        """Call the requested provider; on a retryable Baseten failure, the same open weights on Fireworks."""
        try:
            return await self._attempt(request.provider, request.model, request, media)
        except ProviderError as error:
            fallback = FAILOVER.get((request.provider, request.model))
            if fallback is None or not error.retryable:
                raise
            result = await self._attempt(fallback[0], fallback[1], request, media)
            result.failover_from = request.provider
            return result

    async def _attempt(self, provider: Provider, model: str, request: ModelRequest, media: bytes | None) -> LiveResult:
        authorization = self._keys.authorization(provider)
        seconds = _wav_seconds(media) if request.api == "asr_transcribe" and media else None
        reservation = self._ledger.reserve(self._prices.reserve_for(request, seconds), f"{provider}:{model}")
        cost = 0.0
        try:
            response = await self._send(provider, model, request, media, authorization)
            cost = self._prices.cost_of(request, response, model)
            return LiveResult(response.model_copy(update={"served_by": provider}), cost, provider, None)
        finally:
            self._ledger.settle(reservation, cost)

    async def _send(self, provider: Provider, model: str, request: ModelRequest, media: bytes | None, authorization: str) -> ModelResponse:
        base = BASE_URLS[provider]
        headers = {"Authorization": authorization}
        try:
            if request.api == "chat_completions":
                http_response = await self._http.post(f"{base}/chat/completions", json=chat_body(request, model), headers=headers)
                return parse_chat(self._checked(http_response, provider, model))
            if request.api == "responses":
                http_response = await self._http.post(f"{base}/responses", json=responses_body(request, model), headers=headers)
                return parse_responses(self._checked(http_response, provider, model))
            if request.api == "sam_segmentation":
                return await self._sam(base, model, request, media, headers, provider)
            if request.api == "asr_transcribe":
                files = {
                    "request": (None, json.dumps(asr_request(model)), "application/json"),
                    "audio": ("question.wav", media or b"", "audio/wav"),
                }
                http_response = await self._http.post(
                    f"{base}/asr/transcribe", files=files, headers={**headers, "Accept": "application/json"}
                )
                return parse_asr(self._checked(http_response, provider, model))
        except httpx.TransportError as error:
            raise ProviderError(f"{provider} {model}: {type(error).__name__} before a response arrived", retryable=True) from None
        raise GatewayError(f"unknown model api {request.api}")

    async def _sam(self, base: str, model: str, request: ModelRequest, media: bytes | None, headers: dict[str, str], provider: Provider) -> ModelResponse:
        body = sam_body(request, model, media or b"")
        async with self._http.stream("POST", f"{base}/responses", json=body, headers=headers) as http_response:
            if http_response.status_code >= 400:
                await http_response.aread()
                self._checked(http_response, provider, model)
            events = [event async for event in _sse_events(http_response.aiter_lines())]
        return sam_response(events)

    def _checked(self, response: httpx.Response, provider: Provider, model: str) -> dict[str, Any]:
        if response.status_code >= 400:
            raise ProviderError(
                self._keys.redact(f"{provider} {model} returned HTTP {response.status_code}: {_error_summary(response)}"),
                retryable=response.status_code in (408, 409, 429) or response.status_code >= 500,
            )
        try:
            return response.json()
        except ValueError:
            raise ProviderError(f"{provider} {model} returned a body that is not JSON", retryable=True) from None


def chat_body(request: ModelRequest, model: str) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": model,
        "messages": [m.model_dump() for m in request.messages],
        "max_tokens": request.max_tokens,
        "reasoning_effort": request.reasoning_effort,
    }
    if request.response_schema is not None:
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": RESPONSE_SCHEMA_NAME, "schema": request.response_schema},
        }
    return body


def responses_body(request: ModelRequest, model: str) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": model,
        "input": [m.model_dump() for m in request.messages],
        "max_output_tokens": request.max_tokens,
        "reasoning": {"effort": request.reasoning_effort},
    }
    if request.response_schema is not None:
        body["text"] = {"format": {"type": "json_schema", "name": RESPONSE_SCHEMA_NAME, "schema": request.response_schema}}
    return body


def sam_body(request: ModelRequest, model: str, png: bytes) -> dict[str, Any]:
    prompt = request.messages[-1].content
    image_url = "data:image/png;base64," + base64.b64encode(png).decode("ascii")
    content = [{"type": "input_text", "text": prompt}, {"type": "input_image", "image_url": image_url}]
    return {"model": model, "stream": True, "input": [{"type": "message", "role": "user", "content": content}]}


def asr_request(model: str) -> dict[str, str]:
    return {"model": model, "audioEncoding": "WAV", "mode": ASR_MODES.get(model, "PUSH_TO_TALK")}


def parse_chat(body: dict[str, Any]) -> ModelResponse:
    choice = (body.get("choices") or [{}])[0]
    usage = body.get("usage") or {}
    details = usage.get("completion_tokens_details") or {}
    return ModelResponse(
        content=(choice.get("message") or {}).get("content") or "",
        finish_reason=choice.get("finish_reason") or "unknown",
        usage=TokenUsage(
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            reasoning_tokens=details.get("reasoning_tokens"),
        ),
    )


def parse_responses(body: dict[str, Any]) -> ModelResponse:
    texts = [
        part.get("text", "")
        for item in body.get("output") or []
        if item.get("type") == "message"
        for part in item.get("content") or []
        if part.get("type") == "output_text"
    ]
    if body.get("status") == "incomplete":
        reason = (body.get("incomplete_details") or {}).get("reason")
        finish = "length" if reason == "max_output_tokens" else (reason or "incomplete")
    else:
        finish = "stop" if body.get("status") == "completed" else (body.get("status") or "unknown")
    usage = body.get("usage") or {}
    return ModelResponse(
        content="".join(texts),
        finish_reason=finish,
        usage=TokenUsage(
            prompt_tokens=usage.get("input_tokens"),
            completion_tokens=usage.get("output_tokens"),
            reasoning_tokens=(usage.get("output_tokens_details") or {}).get("reasoning_tokens"),
        ),
    )


def sam_response(events: list[dict[str, Any]]) -> ModelResponse:
    completed = next((e for e in reversed(events) if e.get("type") in ("response.completed", "response.incomplete", "response.failed")), None)
    status = (completed or {}).get("response", {}).get("status")
    text = next((e.get("text", "") for e in events if e.get("type") == "response.output_text.done"), "")
    return ModelResponse(content=text, finish_reason="stop" if status == "completed" else (status or "unknown"), events=events)


def parse_asr(body: dict[str, Any]) -> ModelResponse:
    return ModelResponse(content=body.get("transcript") or "", finish_reason="stop", audio_duration_ms=body.get("audioDurationMs"))


async def _sse_events(lines: Any) -> Any:
    """The JSON payload of every `data:` line of a server-sent event stream, up to `[DONE]`."""
    async for line in lines:
        if not line.startswith("data:"):
            continue
        data = line.removeprefix("data:").strip()
        if data == "[DONE]":
            return
        if data:
            yield json.loads(data)


def _error_summary(response: httpx.Response) -> str:
    """The provider's error code and type, never its full body."""
    try:
        error = response.json().get("error") or {}
    except (ValueError, AttributeError):
        return "no error details"
    if isinstance(error, str):
        return error[:120]
    return " ".join(str(error.get(k)) for k in ("code", "type") if error.get(k)) or "no error details"


def _wav_seconds(wav: bytes) -> float:
    try:
        with wave.open(BytesIO(wav)) as reader:
            return reader.getnframes() / reader.getframerate()
    except (wave.Error, EOFError):
        return 600.0  # unreadable header: reserve the 10-minute maximum the endpoint accepts


class LiveSource:
    """Fresh model calls through a LiveClient. The gateway records each response for later reruns."""

    kind = "live"

    def __init__(self, client: LiveClient, recording_id: str | None = None) -> None:
        self._client = client
        self.recording_id = recording_id

    async def respond(self, key: str, request: ModelRequest, media: bytes | None = None) -> tuple[ModelResponse, float | None]:
        result = await self._client.call(request, media)
        return result.response, result.cost_usd
