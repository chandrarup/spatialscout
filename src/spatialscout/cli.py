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
    benchmark = commands.add_parser("benchmark", help="verify valid and injected claims derived from the audit results; replays stored visual checks")
    benchmark.add_argument("--run-mode", choices=["cached_tool_rerun", "live", "offline"], default="cached_tool_rerun",
                           help="live re-records the visual checks (cents); offline skips them")
    benchmark.add_argument("--env-file", type=Path, default=None)
    commands.add_parser("audit", help="compute the demo's GSE286184 audit results into artifacts/GSE286184/audit/ (needs ingest)")
    commands.add_parser("kpmp", help="measure the two KPMP CODEX participants, freeze thresholds, compute the protein audit and write tiles into artifacts/KPMP/")
    commands.add_parser("contrasts", help="compute every descriptive GSE286184 disease contrast into artifacts/GSE286184/contrasts/ (needs ingest)")
    structures = commands.add_parser(
        "structures", help="SAM 3.1 glomerulus outlines (exploratory) for the demo sections into artifacts/GSE286184/structures/"
    )
    structures.add_argument("--run-mode", choices=["live", "cached_tool_rerun"], default="cached_tool_rerun")
    structures.add_argument("--sections", nargs="*", default=None, help="section ids or names (default: the demo sections)")
    structures.add_argument("--env-file", type=Path, default=None, help="a .env file with the Meta key, when it is not in the environment")
    args = parser.parse_args(argv)
    if args.command == "ingest":
        return _ingest(download=not args.no_download)
    if args.command == "audit":
        return _audit()
    if args.command == "benchmark":
        return asyncio.run(_benchmark(args.run_mode, args.env_file))
    if args.command == "contrasts":
        return _contrasts()
    if args.command == "kpmp":
        return _kpmp()
    if args.command == "structures":
        return asyncio.run(_structures(args.run_mode, args.sections, args.env_file))
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


def _kpmp() -> int:
    """Per-cell tables to SPATIALSCOUT_KPMP_PROCESSED_DIR (git-ignored); thresholds, audit tables, results and tiles
    to artifacts/KPMP/."""
    from .data.kpmp import build
    from .settings import Settings

    settings = Settings.from_env()
    assert settings.kpmp_dir and settings.kpmp_processed_dir and settings.artifacts_dir
    manifest = build(settings.kpmp_dir, settings.kpmp_processed_dir, settings.artifacts_dir)
    print(f"wrote {len(manifest.results)} protein audit results for {len(manifest.participants)} participants to {settings.artifacts_dir / 'KPMP'}")
    return 0


def _audit() -> int:
    """Audit results, controls and composite figures for the demo, written to artifacts/GSE286184/audit/."""
    from .data import DatasetStore
    from .engine.batch import run_batch
    from .settings import Settings, _repo_root

    settings = Settings.from_env()
    assert settings.artifacts_dir
    store = DatasetStore(settings.fixtures_dir, artifacts_dir=settings.artifacts_dir, processed_dir=settings.processed_dir)
    from .engine.conditions import EXPLORATORY_CONDITIONS, PRIMARY_CONDITIONS

    index = run_batch(store, settings.artifacts_dir / "GSE286184" / "audit", _repo_root(), conditions=[*PRIMARY_CONDITIONS, *EXPLORATORY_CONDITIONS])
    print(f"wrote {len(index.entries)} audit results to {settings.artifacts_dir / 'GSE286184' / 'audit'}")
    return 0


def _contrasts() -> int:
    """Descriptive disease contrasts and their composite figures, written to artifacts/GSE286184/contrasts/."""
    from .data import DatasetStore
    from .engine.contrast_batch import run_contrasts
    from .settings import Settings, _repo_root

    settings = Settings.from_env()
    assert settings.artifacts_dir
    store = DatasetStore(settings.fixtures_dir, artifacts_dir=settings.artifacts_dir, processed_dir=settings.processed_dir)
    index = run_contrasts(store, settings.artifacts_dir / "GSE286184" / "contrasts", _repo_root())
    print(f"wrote {len(index.entries)} contrast results to {settings.artifacts_dir / 'GSE286184' / 'contrasts'}")
    return 0


async def _benchmark(run_mode: str, env_file: Path | None) -> int:
    """The verification benchmark (`verify/benchmark.py`): results to artifacts/GSE286184/benchmark/results.json."""
    from datetime import UTC, datetime

    from .contracts import Recording
    from .data import DatasetStore
    from .gateway import LIST_PRICES, ApiKeys, LiveClient, LiveSource, ModelGateway, RecordingWriter, ReplaySource, SpendLedger
    from .settings import Settings
    from .verify.benchmark import RECORDING_ID, recording_info, run_benchmark, write_results

    settings = Settings.from_env()
    assert settings.artifacts_dir
    store = DatasetStore(settings.fixtures_dir, artifacts_dir=settings.artifacts_dir, processed_dir=settings.processed_dir)
    recording_path = settings.fixtures_dir / "benchmark" / "recording.json"

    def clock() -> datetime:
        return datetime.now(UTC)

    client, gateway = None, None
    if run_mode == "live":
        live = settings.live
        if live.daily_budget_usd is None or live.spend_dir is None:
            print("benchmark: live calls need SPATIALSCOUT_DAILY_BUDGET_USD (and optionally SPATIALSCOUT_SPEND_DIR)", file=sys.stderr)
            return 2
        client = LiveClient(ApiKeys.from_env(env_file or live.env_file), SpendLedger(live.spend_dir, live.daily_budget_usd, clock), LIST_PRICES)
        recording_path.unlink(missing_ok=True)
        gateway = ModelGateway(LiveSource(client, RECORDING_ID), clock, run_mode="live", recorder=RecordingWriter(recording_path, recording_info()))
    elif run_mode == "cached_tool_rerun":
        gateway = ModelGateway(ReplaySource(Recording.model_validate_json(recording_path.read_text(encoding="utf-8"))), clock,
                               run_mode="cached_tool_rerun")
    try:
        results = await run_benchmark(store, settings.artifacts_dir, gateway)
    finally:
        if client is not None:
            await client.aclose()
    out = settings.artifacts_dir / "GSE286184" / "benchmark"
    path = write_results(results, out) if run_mode != "offline" else write_results(results, out / "offline")
    summary = results["summary"]["all"]
    print(f"wrote {path}: {summary['valid_claims']} valid and {summary['injected_claims']} injected claims; "
          f"detection {summary['detection']['any_check']}, false rejection {summary['false_rejection']['any_check']}")
    return 0


async def _structures(run_mode: str, wanted: list[str] | None, env_file: Path | None) -> int:
    """SAM 3.1 outlines for the demo sections. Live: one image per crop of up to 16 seed boxes (about $0.0025 each),
    recorded to fixtures/sam/<section_id>.json; cached_tool_rerun replays those recordings with no network call.
    Either way the run, with its image count and cost, goes to artifacts/GSE286184/structures/<section_id>.json."""
    from datetime import UTC, datetime

    from .contracts import Recording
    from .data import DatasetStore
    from .engine.structure_finder import DEMO_SECTIONS, find_structures, recording_info, recording_path, run_path
    from .gateway import LIST_PRICES, ApiKeys, LiveClient, LiveSource, ModelGateway, RecordingWriter, ReplaySource, SpendLedger
    from .settings import Settings

    settings = Settings.from_env()
    assert settings.artifacts_dir
    store = DatasetStore(settings.fixtures_dir, artifacts_dir=settings.artifacts_dir, processed_dir=settings.processed_dir)
    by_name = {s.name: s.section_id for s in store.sections("GSE286184")}
    section_ids = [by_name.get(w, w) for w in (wanted or DEMO_SECTIONS)]

    def clock() -> datetime:
        return datetime.now(UTC)

    client = None
    if run_mode == "live":
        live = settings.live
        if live.daily_budget_usd is None or live.spend_dir is None:
            print("structures: live calls need SPATIALSCOUT_DAILY_BUDGET_USD (and optionally SPATIALSCOUT_SPEND_DIR)", file=sys.stderr)
            return 2
        keys = ApiKeys.from_env(env_file or live.env_file)
        client = LiveClient(keys, SpendLedger(live.spend_dir, live.daily_budget_usd, clock), LIST_PRICES)
    images, cost = 0, 0.0
    try:
        for section_id in section_ids:
            section = store.load_section(section_id)
            path = recording_path(settings.fixtures_dir, section_id)
            if client is not None:
                path.unlink(missing_ok=True)  # a fresh live run replaces the section's stored responses
                recorder = RecordingWriter(path, recording_info(section_id))
                gateway = ModelGateway(LiveSource(client, f"sam-{section_id}"), clock, run_mode="live", recorder=recorder)
            else:
                recording = Recording.model_validate_json(path.read_text(encoding="utf-8"))
                gateway = ModelGateway(ReplaySource(recording), clock, run_mode="cached_tool_rerun")
            run = await find_structures(section, gateway, run_mode, log=print)
            out = run_path(settings.artifacts_dir, section_id)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(run.model_dump_json(indent=1) + "\n", encoding="utf-8")
            counts = {status: sum(p.status == status for p in run.proposals) for status in ("outlined", "fragmented", "empty", "rejected")}
            print(f"{section_id}: {len(run.proposals)} seeds, {counts}; wrote {out}")
            images, cost = images + run.images_sent, cost + run.estimated_cost_usd
    finally:
        if client is not None:
            await client.aclose()
    print(f"structures, {run_mode}: {images} images sent to SAM 3.1 in total, ${cost:.4f}")
    return 0
