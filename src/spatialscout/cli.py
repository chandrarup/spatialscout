"""Command line. `spatialscout serve` runs the API, which also serves the built web app from web/dist.
`spatialscout ingest` downloads any missing GSE286184 file and builds the validated tables and artifacts."""

import argparse
from pathlib import Path

import uvicorn


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="spatialscout")
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="run the API and the built web app")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true", help="restart when Python source changes")
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
