"""Model-call contracts: requests, responses, recordings for replay, and the per-call record (ADR-0003)."""

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from .base import SCHEMA_VERSION, Contract, RunMode

Provider = Literal["meta", "baseten", "fireworks"]

ModelApi = Literal["chat_completions", "responses", "sam_segmentation", "asr_transcribe"]
"""Which provider endpoint a request goes to: OpenAI-style chat completions or responses, SAM 3.1 box-prompt
segmentation (a streamed responses call) or Muse Voice Transcribe (multipart WAV upload)."""


class ChatMessage(Contract):
    role: Literal["system", "user", "assistant"]
    content: str


class ModelRequest(Contract):
    """Everything sent to a provider. Its content hash keys the cache and the replay (ADR-0003),
    so it must never contain ids, timestamps or other run-specific values."""

    provider: Provider
    model: str
    messages: list[ChatMessage]
    response_schema: dict[str, Any] | None = None
    max_tokens: int = Field(default=4000, ge=2000, description="Every model here reasons before answering; a small cap returns empty content.")
    reasoning_effort: Literal["low", "medium", "high"] = "low"
    api: ModelApi = "chat_completions"


class TokenUsage(Contract):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    reasoning_tokens: int | None = None


class ModelResponse(Contract):
    """What a provider returned. `finish_reason` is "length" when the token cap cut the answer short, on either
    endpoint. `served_by` names the provider that answered when it differs from the requested one (failover)."""

    content: str
    finish_reason: str
    usage: TokenUsage | None = None
    served_by: Provider | None = None
    events: list[dict[str, Any]] | None = Field(
        default=None, description="SAM 3.1: the streamed response events, kept so a stored response is parsed exactly as a live one."
    )
    audio_duration_ms: int | None = None


class CacheInput(Contract):
    """A computed input a model request was built from. Part of the cache key, so a changed tool version
    or artifact invalidates the stored response."""

    name: str
    version: str
    sha256: str


class RecordedCall(Contract):
    purpose: str
    cache_key: str
    request: ModelRequest
    inputs: list[CacheInput]
    response: ModelResponse
    latency_ms: int | None = None


class ReplayInfo(Contract):
    """What the replay banner shows about the recording being played."""

    recording_id: str
    recorded_at: datetime
    origin: Literal["live", "hand_authored"] = Field(
        description="live: recorded from real model calls; hand_authored: written for tests without calling a model."
    )
    question: str
    note: str


class Recording(Contract):
    """A recorded investigation's model responses, replayed by content hash of each request."""

    schema_version: str = SCHEMA_VERSION
    info: ReplayInfo
    calls: list[RecordedCall]


class ModelCallRecord(Contract):
    """One model call as the audit log records it and the telemetry pills show it, including whether its
    response was live (`source: live`) or stored (`source: replay`)."""

    call_id: str
    purpose: str
    provider: Provider
    model: str
    cache_key: str
    source: Literal["live", "replay", "cache"]
    recording_id: str | None = None
    started_at: datetime
    latency_ms: int
    finish_reason: str
    usage: TokenUsage | None = None
    estimated_cost_usd: float | None = Field(default=None, description="Spend charged to the live budget; null for stored responses.")
    run_mode: RunMode | None = None
    served_by: Provider | None = Field(default=None, description="The provider that answered; differs from `provider` after failover.")
    failover_from: Provider | None = None
    error_code: str | None = Field(default=None, description="Set when the call produced no usable response.")
