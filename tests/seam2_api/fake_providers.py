"""Fake model providers for live runs in seam-2 tests, behind an httpx MockTransport.

Bodies follow the shapes recorded from the real providers on Nov 2 (chat completions with
`completion_tokens_details.reasoning_tokens`; see fixtures/smoke/). Answers come from the hand-authored recording,
so the live run plans and drafts exactly what the cached tool rerun does. Nothing here opens a socket.
"""

import json
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx2 as httpx

from spatialscout.gateway import ApiKeys, PriceBook, TokenPrice

REPO = Path(__file__).resolve().parents[2]
HAND_AUTHORED = REPO / "fixtures" / "recordings" / "syn01-podocyte-lrp2" / "recording.json"

PASSCODE = "correct horse battery staple"
FAKE_KEYS = {"meta": "LLM_1234_fake-meta-key-value", "baseten": "bt-fake-baseten-key-value", "fireworks": "fw-fake-fireworks-key-value"}

# A fake price: every chat call reserves, and costs, exactly $1.00 (4,000 output tokens at $250 per million,
# input free), whatever its prompt.
OUTPUT_TOKENS = 4000
FAKE_PRICES = PriceBook(
    tokens={
        model: TokenPrice(0.0, 250.0)
        for model in ("muse-wonder-1.0", "muse-spark-1.3", "meta-models/muse-spark-open", "accounts/fireworks/models/muse-spark-open")
    },
    per_image={"sam-3.1": 0.01},
    per_audio_second={"muse-voice-transcribe-1.0": 0.001},
)


def fake_keys() -> ApiKeys:
    return ApiKeys(FAKE_KEYS)  # type: ignore[arg-type]


def recorded_answers() -> dict[str, str]:
    """The hand-authored answer for each model, as the fake providers return it."""
    calls = json.loads(HAND_AUTHORED.read_text())["calls"]
    return {call["request"]["model"]: call["response"]["content"] for call in calls}


@dataclass
class Sent:
    host: str
    path: str
    authorization: str | None
    body: dict[str, Any]


@dataclass
class FakeProviders:
    """Answers chat completions as the real providers do. `status` forces an HTTP status per host;
    `answers` overrides content per model (a list is served in order, one item per call)."""

    status: dict[str, int] = field(default_factory=dict)
    answers: dict[str, Any] = field(default_factory=dict)
    finish_reason: str = "stop"
    delay_s: float = 0.0
    sent: list[Sent] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self)

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else {}
        with self._lock:
            self.sent.append(Sent(request.url.host, request.url.path, request.headers.get("authorization"), body))
        if self.delay_s:
            time.sleep(self.delay_s)
        status = self.status.get(request.url.host, 200)
        if status != 200:
            return httpx.Response(status, json={"error": {"code": "forced", "type": "test_error", "message": "forced failure"}})
        return httpx.Response(200, json=self._chat_body(body["model"]))

    def _chat_body(self, model: str) -> dict[str, Any]:
        content = self._answer(model)
        return {
            "id": "chatcmpl-fake",
            "object": "chat.completion",
            "model": model,
            "choices": [{"index": 0, "finish_reason": self.finish_reason, "message": {"role": "assistant", "content": content}}],
            "usage": {
                "prompt_tokens": 1200,
                "completion_tokens": OUTPUT_TOKENS,
                "total_tokens": 1200 + OUTPUT_TOKENS,
                "completion_tokens_details": {"reasoning_tokens": 300},
            },
        }

    def _answer(self, model: str) -> str:
        if self.finish_reason == "length":
            return ""
        override = self.answers.get(model)
        if isinstance(override, list):
            with self._lock:
                return override.pop(0)
        if override is not None:
            return override
        answers = recorded_answers()
        return answers.get(model) or answers["meta-models/muse-spark-open"]

    def calls_to(self, host_fragment: str) -> list[Sent]:
        return [s for s in self.sent if host_fragment in s.host]
