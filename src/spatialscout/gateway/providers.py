"""Where each provider lives, what its calls cost, and the API keys, which never leave this process.

Facts come from `docs/research/` (checked live on Nov 2): every endpoint is OpenAI-compatible with a Bearer key;
Muse Spark Open has a different model id on Baseten and Fireworks.
"""

import math
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from ..contracts import ModelRequest, ModelResponse, Provider
from .errors import MissingApiKey

BASE_URLS: dict[Provider, str] = {
    "meta": "https://api.meta.ai/v1",
    "baseten": "https://inference.baseten.co/v1",
    "fireworks": "https://api.fireworks.ai/inference/v1",
}

KEY_ENV_VARS: dict[Provider, str] = {"meta": "META_API_KEY", "baseten": "BASETEN_API_KEY", "fireworks": "FIREWORKS_API_KEY"}

# Muse Spark Open on Baseten fails over to the same open weights on Fireworks.
FAILOVER: dict[tuple[Provider, str], tuple[Provider, str]] = {
    ("baseten", "meta-models/muse-spark-open"): ("fireworks", "accounts/fireworks/models/muse-spark-open"),
}


@dataclass(frozen=True)
class TokenPrice:
    input_per_million: float
    output_per_million: float


@dataclass(frozen=True)
class PriceBook:
    """USD prices used to reserve budget before a call and to settle it after. Tests swap in fake prices."""

    tokens: Mapping[str, TokenPrice]
    per_image: Mapping[str, float]
    per_audio_second: Mapping[str, float]

    def reserve_for(self, request: ModelRequest, media_seconds: float | None = None) -> float:
        """The most this call can cost: every prompt character as a token (an overestimate) and the whole
        output cap. Reservations are settled to the real cost afterwards."""
        if request.api == "sam_segmentation":
            return self.per_image[request.model]
        if request.api == "asr_transcribe":
            return self.per_audio_second[request.model] * math.ceil(media_seconds or 0)
        price = self._token_price(request.model)
        prompt_tokens = sum(len(message.content) for message in request.messages)
        return (prompt_tokens * price.input_per_million + request.max_tokens * price.output_per_million) / 1e6

    def cost_of(self, request: ModelRequest, response: ModelResponse, model: str) -> float:
        if request.api == "sam_segmentation":
            return self.per_image[model]
        if request.api == "asr_transcribe":
            return self.per_audio_second[model] * ((response.audio_duration_ms or 0) // 1000)
        price = self._token_price(model)
        usage = response.usage
        if usage is None or usage.prompt_tokens is None or usage.completion_tokens is None:
            return self.reserve_for(request)
        return (usage.prompt_tokens * price.input_per_million + usage.completion_tokens * price.output_per_million) / 1e6

    def _token_price(self, model: str) -> TokenPrice:
        try:
            return self.tokens[model]
        except KeyError:
            raise KeyError(f"no price for model {model}; add it to the price book before calling it live") from None


SPARK_OPEN = TokenPrice(1.25, 4.25)

# Pay-as-you-go list prices, Nov 2 2026 (docs/research/meta-platform.md, hackathon-and-partners.md).
LIST_PRICES = PriceBook(
    tokens={
        "muse-wonder-1.0": TokenPrice(4.00, 20.00),
        "muse-spark-1.3": TokenPrice(1.25, 4.25),
        "meta-models/muse-spark-open": SPARK_OPEN,
        "accounts/fireworks/models/muse-spark-open": SPARK_OPEN,
    },
    per_image={"sam-3.1": 2.50 / 1000},
    per_audio_second={"muse-voice-transcribe-1.0": 0.18 / 3600},
)


class ApiKeys:
    """Provider API keys. They are only ever written into an Authorization header; `repr` never shows them."""

    def __init__(self, keys: Mapping[Provider, str]) -> None:
        self._keys = {provider: key for provider, key in keys.items() if key}

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> "ApiKeys":
        """Keys from the environment, falling back to a `.env` file (never logged, never copied anywhere)."""
        file_values: dict[str, str] = {}
        if env_file is not None and env_file.is_file():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                name, sep, value = line.partition("=")
                if sep and not name.strip().startswith("#"):
                    file_values[name.strip()] = value.strip().strip('"').strip("'")
        return cls({p: os.environ.get(var) or file_values.get(var, "") for p, var in KEY_ENV_VARS.items()})

    def has(self, provider: Provider) -> bool:
        return provider in self._keys

    def authorization(self, provider: Provider) -> str:
        if provider not in self._keys:
            raise MissingApiKey(f"no API key for {provider}: set {KEY_ENV_VARS[provider]} on the server")
        return f"Bearer {self._keys[provider]}"

    def redact(self, text: str) -> str:
        """Remove any key value from text bound for an event, the audit log or a log line."""
        for key in self._keys.values():
            text = text.replace(key, "[redacted]")
        return text

    def __repr__(self) -> str:
        return f"ApiKeys(providers={sorted(self._keys)})"
