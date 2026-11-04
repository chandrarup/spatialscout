"""Record the stored transcription of the sample spoken question, live, for every dataset's panel keywords.

    uv run python scripts/record_voice_sample.py [--env-file PATH] [--spend-dir PATH]

Sends `fixtures/voice/question.wav` (the smoke clip: "Does podocyte LRP2 survive nucleus only assignment?") to
Muse Voice Transcribe once per dataset, biased toward that dataset's panel genes exactly as
`POST /api/voice/transcribe` does, and writes every response to `fixtures/voice/recording.json`. A cached tool
rerun of the route then replays it with no network call. Costs a fraction of a cent; capped at $0.05.
"""

import argparse
import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

from spatialscout.contracts import ReplayInfo
from spatialscout.data import DatasetStore
from spatialscout.gateway import LIST_PRICES, ApiKeys, LiveClient, LiveSource, ModelGateway, RecordingWriter, SpendLedger

REPO = Path(__file__).resolve().parents[1]
VOICE = REPO / "fixtures" / "voice"
RECORDING_ID = "voice-sample"


def clock() -> datetime:
    return datetime.now(UTC)


async def main(env_file: Path, spend_dir: Path) -> int:
    store = DatasetStore(REPO / "fixtures", artifacts_dir=REPO / "artifacts", processed_dir=REPO / "data" / "processed" / "GSE286184")
    info = ReplayInfo(
        recording_id=RECORDING_ID,
        recorded_at=clock().replace(microsecond=0),
        origin="live",
        question="Does podocyte LRP2 survive nucleus only assignment?",
        note="The sample spoken question, recorded live by scripts/record_voice_sample.py with each dataset's panel as keywords.",
    )
    client = LiveClient(ApiKeys.from_env(env_file), SpendLedger(spend_dir, 0.05, clock), LIST_PRICES)
    recorder = RecordingWriter(VOICE / "recording.json", info)
    gateway = ModelGateway(LiveSource(client, RECORDING_ID), clock, run_mode="live", recorder=recorder)
    wav = (VOICE / "question.wav").read_bytes()
    try:
        for dataset_id in store.dataset_ids():
            transcript, record = await gateway.transcribe("question", wav, store.manifest(dataset_id).panel)
            print(f"{dataset_id:12} {record.latency_ms:5} ms  {transcript}")
    finally:
        await client.aclose()
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--env-file", type=Path, default=REPO / ".env")
    parser.add_argument("--spend-dir", type=Path, default=REPO / "data" / "spend")
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.env_file, args.spend_dir)))
