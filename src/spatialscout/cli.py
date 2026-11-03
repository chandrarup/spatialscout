"""Command line.

- `spatialscout serve` runs the API, which also serves the built web app from web/dist.
- `spatialscout ingest` downloads any missing GSE286184 file and builds the validated tables and artifacts.
- `spatialscout smoke` makes one tiny call per provider, model and endpoint. `--run-mode live` calls the
  providers under the daily budget and records the responses; `--run-mode cached_tool_rerun` (the default)
  replays the recording without any network call and prints the same results.
"""

import argparse
import asyncio
import sys
from pathlib import Path

import uvicorn


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="spatialscout")
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="run the API and the built web app")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true", help="restart when Python source changes")
    smoke = commands.add_parser("smoke", help="one tiny call per provider and model, live and recorded, or replayed")
    smoke.add_argument("--run-mode", choices=["live", "cached_tool_rerun"], default="cached_tool_rerun")
    smoke.add_argument("--dir", type=Path, default=None, help="where the smoke image, audio and recording live (default fixtures/smoke)")
    smoke.add_argument("--env-file", type=Path, default=None, help="a .env file with the provider keys, when they are not in the environment")
    ingest = commands.add_parser("ingest", help="download missing GSE286184 files, then validate and label all 22 sections")
    ingest.add_argument("--no-download", action="store_true", help="fail on a missing raw file instead of fetching it")
    args = parser.parse_args(argv)
    if args.command == "ingest":
        return _ingest(download=not args.no_download)
    if args.command == "serve":
        uvicorn.run(
            "spatialscout.api:create_app",
            factory=True,
            host=args.host,
            port=args.port,
            reload=args.reload,
            reload_dirs=[str(Path(__file__).resolve().parent)] if args.reload else None,
        )
    elif args.command == "smoke":
        return asyncio.run(_smoke(args.run_mode, args.dir, args.env_file))
    return 0


async def _smoke(run_mode: str, smoke_dir: Path | None, env_file: Path | None) -> int:
    from datetime import UTC, datetime

    from .contracts import Recording
    from .gateway import LIST_PRICES, ApiKeys, LiveClient, LiveSource, ModelGateway, RecordingWriter, ReplaySource, SpendLedger
    from .gateway.smoke import IMAGE_FILE, RECORDING_FILE, SMOKE_RECORDING_ID, disc_png, run_smoke, smoke_info
    from .settings import Settings

    settings = Settings.from_env()
    smoke_dir = smoke_dir or settings.fixtures_dir / "smoke"
    recording_path = smoke_dir / RECORDING_FILE

    def clock() -> datetime:
        return datetime.now(UTC)

    client = None
    if run_mode == "live":
        live = settings.live
        if live.daily_budget_usd is None or live.spend_dir is None:
            print("smoke: live calls need SPATIALSCOUT_DAILY_BUDGET_USD (and optionally SPATIALSCOUT_SPEND_DIR)", file=sys.stderr)
            return 2
        if not (smoke_dir / IMAGE_FILE).is_file():
            (smoke_dir / IMAGE_FILE).write_bytes(disc_png())
        keys = ApiKeys.from_env(env_file or live.env_file)
        client = LiveClient(keys, SpendLedger(live.spend_dir, live.daily_budget_usd, clock), LIST_PRICES)
        gateway = ModelGateway(
            LiveSource(client, SMOKE_RECORDING_ID), clock, run_mode="live", recorder=RecordingWriter(recording_path, smoke_info())
        )
    else:
        recording = Recording.model_validate_json(recording_path.read_text(encoding="utf-8"))
        gateway = ModelGateway(ReplaySource(recording), clock, run_mode="cached_tool_rerun")
    try:
        results = await run_smoke(gateway, smoke_dir)
    finally:
        if client is not None:
            await client.aclose()
    print(f"provider smoke check, {run_mode}:")
    for result in results:
        print(result.line())
    if run_mode == "live":
        print(f"recorded {len(results)} responses in {recording_path}; spent ${sum(r.cost_usd or 0 for r in results):.4f}")
    return 0


def _ingest(download: bool) -> int:
    """Raw files go to SPATIALSCOUT_RAW_DIR, validated tables to SPATIALSCOUT_PROCESSED_DIR (both git-ignored),
    and the manifest, capability report and label rules to artifacts/GSE286184/."""
    from .data.gse286184 import Paths, download_missing, ingest
    from .settings import Settings

    settings = Settings.from_env()
    assert settings.raw_dir and settings.processed_dir and settings.artifacts_dir
    if download:
        print(f"{download_missing(settings.raw_dir)} raw files downloaded into {settings.raw_dir}")
    ingest(Paths(settings.raw_dir, settings.processed_dir, settings.artifacts_dir / "GSE286184"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
