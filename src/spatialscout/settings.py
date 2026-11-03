"""Runtime settings. Paths default to this checkout's layout; environment variables override them
(needed once the package is installed outside the repo, as on Modal)."""

import os
from dataclasses import dataclass
from pathlib import Path

from .contracts import RunMode


def _repo_root() -> Path:
    override = os.environ.get("SPATIALSCOUT_ROOT")
    return Path(override) if override else Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    fixtures_dir: Path
    recordings_dir: Path
    investigations_dir: Path
    web_dist: Path | None
    dataset_id: str = "synthetic"
    default_run_mode: RunMode = "cached_tool_rerun"
    # Each SSE connection ends after this many seconds and the client reconnects with `after_seq`, so a host that
    # cuts long requests (Modal, at 150 s) never cuts a stream mid-event.
    stream_window_seconds: float = 110.0

    @classmethod
    def from_env(cls) -> "Settings":
        root = _repo_root()
        env = os.environ.get
        return cls(
            fixtures_dir=Path(env("SPATIALSCOUT_FIXTURES_DIR", str(root / "fixtures"))),
            recordings_dir=Path(env("SPATIALSCOUT_RECORDINGS_DIR", str(root / "fixtures" / "recordings"))),
            investigations_dir=Path(env("SPATIALSCOUT_INVESTIGATIONS_DIR", str(root / "data" / "investigations"))),
            web_dist=Path(env("SPATIALSCOUT_WEB_DIST", str(root / "web" / "dist"))),
            stream_window_seconds=float(env("SPATIALSCOUT_STREAM_WINDOW_SECONDS", "110")),
        )
