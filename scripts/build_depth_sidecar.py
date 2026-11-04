"""Build the measured-depth sidecar for the sections the featured recording cites as evidence.

Usage:  uv run python scripts/build_depth_sidecar.py [SECTION_ID ...]      (or `make depth`)

For each section: read `z_location` from the deposited `*_transcripts.parquet.gz` (gzip-wrapped parquet), join it to
the validated molecules by transcript id (one to one, x/y must agree), and write `depth.parquet` and `depth.json`
beside the processed tables (git-ignored, shipped to Modal with them) plus a copy of `depth.json` under
`artifacts/GSE286184/depth/` (committed). The frozen molecule tables, audit artifacts and recordings are not touched.
Xenium's transcripts table gives x, y and z in micrometres; x and y match the validated coordinates exactly.
"""

import gzip
import hashlib
import io
import json
import sys
from pathlib import Path

import pandas as pd

from spatialscout.contracts import DepthSource
from spatialscout.engine.depth import build_depth_sidecar
from spatialscout.settings import Settings

REPO = Path(__file__).resolve().parents[1]
RECORDING = REPO / "fixtures" / "recordings" / "gse286184-two-part-hypothesis" / "investigation" / "artifacts"
DATASET = "GSE286184"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evidence_sections() -> list[str]:
    out: list[str] = []
    for path in sorted(RECORDING.glob("fnd-*.json")):
        finding = json.loads(path.read_text())
        rank1 = next((r for r in finding.get("evidence_regions", []) if r["rank"] == 1), None)
        if rank1 and rank1["region"]["section_id"] not in out:
            out.append(rank1["region"]["section_id"])
    return out


def build(section_id: str, settings: Settings) -> DepthSource:
    assert settings.raw_dir and settings.processed_dir and settings.artifacts_dir
    raw_path = next((settings.raw_dir / section_id).glob("*_transcripts.parquet.gz"))
    molecules_path = settings.processed_dir / section_id / "molecules.parquet"
    raw = pd.read_parquet(io.BytesIO(gzip.open(raw_path).read()), columns=["transcript_id", "x_location", "y_location", "z_location"])
    table, stats = build_depth_sidecar(pd.read_parquet(molecules_path, columns=["molecule_id", "x", "y"]), raw)
    out = settings.processed_dir / section_id / "depth.parquet"
    table.to_parquet(out, index=False)
    source = DepthSource(
        dataset_id=DATASET,
        section_id=section_id,
        coordinate_note="Xenium transcripts table x_location, y_location, z_location in µm; x and y equal the validated molecule coordinates, z is measured depth.",
        raw_file=raw_path.name,
        raw_sha256=sha256(raw_path),
        molecules_sha256=sha256(molecules_path),
        sidecar_sha256=sha256(out),
        **stats,
    )
    text = source.model_dump_json(indent=2) + "\n"
    (settings.processed_dir / section_id / "depth.json").write_text(text)
    committed = settings.artifacts_dir / DATASET / "depth"
    committed.mkdir(parents=True, exist_ok=True)
    (committed / f"{section_id}.json").write_text(text)
    return source


def main(argv: list[str]) -> int:
    settings = Settings.from_env()
    for section_id in argv or evidence_sections():
        s = build(section_id, settings)
        print(f"{section_id}: {s.with_depth:,} of {s.molecules:,} molecules with z {s.z_min:.2f}–{s.z_max:.2f} µm; max x/y disagreement {s.max_xy_disagreement_um} µm")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
