"""Runtime settings. Paths default to this checkout's layout; environment variables override them
(needed once the package is installed outside the repo, as on Modal)."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast, get_args

from .contracts import RunMode


def _repo_root() -> Path:
    override = os.environ.get("SPATIALSCOUT_ROOT")
    return Path(override) if override else Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class LiveSettings:
    """Live runs (ADR-0003). Without both a passcode and a daily budget, live runs are refused.

    - `SPATIALSCOUT_LIVE_PASSCODE`: the passcode a client sends in the `X-Live-Passcode` header
    - `SPATIALSCOUT_DAILY_BUDGET_USD`: the most live calls may spend per UTC day
    - `SPATIALSCOUT_SPEND_DIR`: where the file-locked spend ledger lives (a shared volume when deployed)
    - `SPATIALSCOUT_ENV_FILE`: a `.env` file to read provider keys from when they are not in the environment
    """

    passcode: str | None = field(default=None, repr=False)
    daily_budget_usd: float | None = None
    spend_dir: Path | None = None
    env_file: Path | None = None

    @property
    def configured(self) -> bool:
        return bool(self.passcode) and self.daily_budget_usd is not None and self.spend_dir is not None


@dataclass(frozen=True)
class Settings:
    fixtures_dir: Path
    recordings_dir: Path
    investigations_dir: Path
    web_dist: Path | None
    dataset_id: str = "synthetic"
    default_run_mode: RunMode = "cached_tool_rerun"
    artifacts_dir: Path | None = None
    """Committed derived artifacts, such as artifacts/GSE286184/ (manifest, capability report, label rules)."""
    processed_dir: Path | None = None
    """Validated GSE286184 tables written by `spatialscout ingest` (git-ignored)."""
    raw_dir: Path | None = None
    """Raw GSE286184 GEO files (git-ignored); in a worktree, point it at the main checkout's data/raw/GSE286184."""
    # Each SSE connection ends after this many seconds and the client reconnects with `after_seq`, so a host that
    # cuts long requests (Modal, at 150 s) never cuts a stream mid-event.
    stream_window_seconds: float = 110.0
    live: LiveSettings = LiveSettings()

    @classmethod
    def from_env(cls) -> "Settings":
        root = _repo_root()
        env = os.environ.get
        budget = env("SPATIALSCOUT_DAILY_BUDGET_USD")
        run_mode = env("SPATIALSCOUT_DEFAULT_RUN_MODE", "cached_tool_rerun")
        if run_mode not in get_args(RunMode):
            raise ValueError(f"SPATIALSCOUT_DEFAULT_RUN_MODE must be one of {get_args(RunMode)}, not {run_mode!r}")
        return cls(
            fixtures_dir=Path(env("SPATIALSCOUT_FIXTURES_DIR", str(root / "fixtures"))),
            recordings_dir=Path(env("SPATIALSCOUT_RECORDINGS_DIR", str(root / "fixtures" / "recordings"))),
            investigations_dir=Path(env("SPATIALSCOUT_INVESTIGATIONS_DIR", str(root / "data" / "investigations"))),
            web_dist=Path(env("SPATIALSCOUT_WEB_DIST", str(root / "web" / "dist"))),
            default_run_mode=cast(RunMode, run_mode),
            artifacts_dir=Path(env("SPATIALSCOUT_ARTIFACTS_DIR", str(root / "artifacts"))),
            processed_dir=Path(env("SPATIALSCOUT_PROCESSED_DIR", str(root / "data" / "processed" / "GSE286184"))),
            raw_dir=Path(env("SPATIALSCOUT_RAW_DIR", str(root / "data" / "raw" / "GSE286184"))),
            stream_window_seconds=float(env("SPATIALSCOUT_STREAM_WINDOW_SECONDS", "110")),
            live=LiveSettings(
                passcode=env("SPATIALSCOUT_LIVE_PASSCODE") or None,
                daily_budget_usd=float(budget) if budget else None,
                spend_dir=Path(env("SPATIALSCOUT_SPEND_DIR", str(root / "data" / "spend"))),
                env_file=Path(env("SPATIALSCOUT_ENV_FILE", str(root / ".env"))),
            ),
        )
