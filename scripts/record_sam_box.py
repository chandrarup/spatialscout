"""Record SAM 3.1's live response to drawn boxes, for the box-prompt route's cached tool rerun and its seam-2 test.

Usage:  SPATIALSCOUT_DAILY_BUDGET_USD=0.05 uv run python scripts/record_sam_box.py --env-file <main checkout>/.env

One image per box (about $0.0025 each), written to fixtures/sam/user_boxes.json. Not part of `make fixtures`: only a
live call can record SAM, so a hand-authored stand-in would prove nothing. Re-record after changing the rendering.
"""

import argparse
import asyncio
from datetime import UTC, datetime
from pathlib import Path

from spatialscout.contracts import Region
from spatialscout.data import DatasetStore
from spatialscout.engine.structure_finder import outline_box, recording_info, recording_path
from spatialscout.gateway import LIST_PRICES, ApiKeys, LiveClient, LiveSource, ModelGateway, RecordingWriter, SpendLedger
from spatialscout.settings import Settings

# SYN-01's glomerulus (radius 33 µm around (60, 75)), enclosed; the seam-2 test draws the same box.
BOXES = [Region(section_id="SYN-01", x0=25.0, y0=40.0, x1=95.0, y1=110.0)]


async def main(env_file: Path | None) -> None:
    settings = Settings.from_env()
    live = settings.live
    assert live.daily_budget_usd is not None and live.spend_dir is not None, "set SPATIALSCOUT_DAILY_BUDGET_USD"
    store = DatasetStore(settings.fixtures_dir, artifacts_dir=settings.artifacts_dir, processed_dir=settings.processed_dir)

    def clock() -> datetime:
        return datetime.now(UTC)

    client = LiveClient(ApiKeys.from_env(env_file or live.env_file), SpendLedger(live.spend_dir, live.daily_budget_usd, clock), LIST_PRICES)
    path = recording_path(settings.fixtures_dir, "user_boxes")
    recorder = RecordingWriter(path, recording_info("user_boxes"))
    gateway = ModelGateway(LiveSource(client, "sam-user_boxes"), clock, run_mode="live", recorder=recorder)
    try:
        for box in BOXES:
            run = await outline_box(store.load_section(box.section_id), box, gateway, "live")
            statuses = [p.status for p in run.proposals]
            print(f"{box.section_id} {box.x0},{box.y0}-{box.x1},{box.y1}: {statuses}, {run.images_sent} image, ${run.estimated_cost_usd:.4f}")
    finally:
        await client.aclose()
    print(f"recorded {len(BOXES)} responses in {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=None)
    asyncio.run(main(parser.parse_args().env_file))
