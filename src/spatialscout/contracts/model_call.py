"""Model-call contracts: requests, responses, recordings for replay, and the per-call record (ADR-0003)."""

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from .base import SCHEMA_VERSION, Contract

Provider = Literal["meta", "baseten", "fireworks"]


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
    max_tokens: int = 4000
    reasoning_effort: Literal["low", "medium", "high"] = "low"


class TokenUsage(Contract):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    reasoning_tokens: int | None = None


class ModelResponse(Contract):
    content: str
    finish_reason: str
    usage: TokenUsage | None = None


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
    """One model call as the audit log records it, including whether its response was live or replayed."""

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
    estimated_cost_usd: float | None = None
