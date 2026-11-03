"""The provider smoke check: one tiny call per provider, model and endpoint, through the gateway.

`spatialscout smoke --run-mode live` makes the calls (a few cents, under the daily budget) and records every
response in `fixtures/smoke/recording.json`; `--run-mode cached_tool_rerun` replays that recording with no
network call and must print identical results. The chat calls ask for a real contract (`ClaimDraft`, whose
schema has `$defs`), so they also show each provider accepts a production response schema.
"""

import struct
import zlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ..contracts import ChatMessage, ClaimDraft, ModelApi, ModelRequest, Provider, ReplayInfo, canonical_json
from .gateway import ModelGateway
from .sam import Box

SMOKE_RECORDING_ID = "provider-smoke"
IMAGE_FILE, AUDIO_FILE, RECORDING_FILE = "circles.png", "question.wav", "recording.json"

CHAT_CALLS: list[tuple[Provider, str, ModelApi]] = [
    ("meta", "muse-wonder-1.0", "chat_completions"),
    ("meta", "muse-wonder-1.0", "responses"),
    ("meta", "muse-spark-1.3", "chat_completions"),
    ("meta", "muse-spark-1.3", "responses"),
    ("baseten", "meta-models/muse-spark-open", "chat_completions"),
    ("fireworks", "accounts/fireworks/models/muse-spark-open", "chat_completions"),
]

SMOKE_PROMPT = (
    "Write one cautious sentence saying that nucleus-only assignment keeps 3 of the 4 LRP2 molecules counted toward "
    "podocytes under the default condition. In `cited`, give 3 as `kept` with source `conditions[nucleus_only].molecules` "
    "and 4 as `total` with source `conditions[default].molecules`. Respond with JSON that matches the response schema."
)

# A 96 x 64 image with two filled discs; SAM is prompted with a box around each.
IMAGE_SIZE = (96, 64)
DISCS = [(30, 30, 12), (70, 34, 9)]  # centre x, centre y, radius, in pixels
BOXES = [Box(16, 16, 45, 45), Box(59, 23, 82, 46)]


@dataclass(frozen=True)
class SmokeResult:
    provider: str
    model: str
    api: str
    source: str
    served_by: str
    latency_ms: int
    tokens: int | None
    cost_usd: float | None
    output: str

    def line(self) -> str:
        cost = "-" if self.cost_usd is None else f"${self.cost_usd:.5f}"
        return f"{self.provider:9} {self.model:42} {self.api:16} {self.source:6} {self.latency_ms:6} ms {cost:>10}  {self.output}"


def smoke_info() -> ReplayInfo:
    return ReplayInfo(
        recording_id=SMOKE_RECORDING_ID,
        recorded_at=datetime.now(UTC).replace(microsecond=0),
        origin="live",
        question="Provider smoke check: one tiny call per provider, model and endpoint.",
        note="Recorded by `spatialscout smoke --run-mode live`.",
    )


async def run_smoke(gateway: ModelGateway, smoke_dir: Path) -> list[SmokeResult]:
    results = []
    for provider, model, api in CHAT_CALLS:
        request = ModelRequest(
            provider=provider,
            model=model,
            api=api,
            messages=[ChatMessage(role="user", content=SMOKE_PROMPT)],
            response_schema=ClaimDraft.model_json_schema(),
        )
        draft, record = await gateway.complete_json(f"smoke:{api}", request, [], ClaimDraft)
        results.append(_result(record, api, canonical_json(draft.model_dump(mode="json"))))
    width, height = IMAGE_SIZE
    segmentation, record = await gateway.segment_boxes("smoke:sam", (smoke_dir / IMAGE_FILE).read_bytes(), width, height, BOXES)
    masks = "; ".join(
        f"object {o.object_id} box {o.box.left},{o.box.top}-{o.box.right},{o.box.bottom} mask {o.mask.shape[1]}x{o.mask.shape[0]} "
        f"area {int(o.mask.sum())}"
        for o in segmentation.objects
    )
    results.append(_result(record, "sam_segmentation", masks))
    transcript, record = await gateway.transcribe("smoke:transcribe", (smoke_dir / AUDIO_FILE).read_bytes())
    results.append(_result(record, "asr_transcribe", transcript))
    return results


def _result(record, api: str, output: str) -> SmokeResult:
    usage = record.usage
    tokens = None if usage is None or usage.completion_tokens is None else (usage.prompt_tokens or 0) + usage.completion_tokens
    return SmokeResult(
        provider=record.provider,
        model=record.model,
        api=api,
        source=record.source,
        served_by=record.served_by or record.provider,
        latency_ms=record.latency_ms,
        tokens=tokens,
        cost_usd=record.estimated_cost_usd,
        output=output,
    )


def disc_png() -> bytes:
    """The smoke image as a greyscale PNG, written with zlib so no imaging library is needed."""
    width, height = IMAGE_SIZE
    rows = b"".join(
        b"\x00" + bytes(255 if any((x - cx) ** 2 + (y - cy) ** 2 <= r * r for cx, cy, r in DISCS) else 0 for x in range(width))
        for y in range(height)
    )

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b"")
