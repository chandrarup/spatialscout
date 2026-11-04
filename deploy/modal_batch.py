"""SpatialScout batch job on Modal (ADR-0004): one lightweight operation per GSE286184 section, fanned out over
all 22 sections with `.map()`, logging the runtime and the estimated compute cost.

Run:  make modal-batch   (writes artifacts/modal_batch_gse286184.json)

Today's per-section operation fetches the section's GEO files into the `spatialscout-raw` Volume (skipping files
already there) and reports their checksums and the section's molecule and cell counts. Later tickets swap in real
per-section tools; the fan-out and the cost log stay. It is a separate app from the web app so that `modal run`
never starts a second web container beside the deployed one.
"""

import gzip
import hashlib
import json
import re
import shutil
import tempfile
import time
import urllib.request
from pathlib import Path

import modal

app = modal.App("spatialscout-batch")
raw_volume = modal.Volume.from_name("spatialscout-raw", create_if_missing=True)

GEO_SAMPLES = "https://ftp.ncbi.nlm.nih.gov/geo/samples/GSM8720nnn"
# The 22 Xenium sections of GSE286184 (docs/research/data-readiness.md): GSM8720409 (x1) to GSM8720430 (x22).
SECTIONS = [f"GSM{8720409 + i}" for i in range(22)]
RAW_MOUNT = "/raw"
BATCH_CPU = 1.0
BATCH_MEMORY_MIB = 1024
# Modal list prices, checked at https://modal.com/pricing on 2026-11-02: CPU per physical core and memory per GiB.
CPU_USD_PER_CORE_SECOND = 0.0000131
MEMORY_USD_PER_GIB_SECOND = 0.00000222

batch_image = modal.Image.debian_slim(python_version="3.12").uv_pip_install("pyarrow==21.0.0")


def _fetch(url: str, destination: Path) -> int:
    """Download `url` to `destination` unless a file of the same size is already there. Returns bytes downloaded."""
    with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=60) as head:
        size = int(head.headers["Content-Length"])
    if destination.is_file() and destination.stat().st_size == size:
        return 0
    partial = destination.with_suffix(destination.suffix + ".partial")
    with urllib.request.urlopen(url, timeout=300) as response, partial.open("wb") as out:
        shutil.copyfileobj(response, out)
    partial.replace(destination)
    return size


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


@app.function(image=batch_image, volumes={RAW_MOUNT: raw_volume}, cpu=BATCH_CPU, memory=BATCH_MEMORY_MIB, timeout=900, retries=2)
def fetch_section(gsm: str) -> dict:
    """Fetch one section's GEO files into the raw Volume, then report their checksums and its molecule and cell
    counts. Later tickets swap this for real per-section tools; the fan-out and the cost log stay."""
    import pyarrow.parquet as pq

    started = time.perf_counter()
    directory_url = f"{GEO_SAMPLES}/{gsm}/suppl/"
    with urllib.request.urlopen(directory_url, timeout=60) as listing:
        names = sorted(set(re.findall(rf'href="({gsm}_[^"/]+)"', listing.read().decode())))
    if not names:
        raise RuntimeError(f"no supplementary files listed at {directory_url}")
    section_dir = Path(RAW_MOUNT) / "GSE286184" / gsm
    section_dir.mkdir(parents=True, exist_ok=True)
    downloaded = 0
    files = []
    for name in names:
        downloaded += _fetch(directory_url + name, section_dir / name)
        files.append({"name": name, "bytes": (section_dir / name).stat().st_size, "sha256": _sha256(section_dir / name)})

    transcripts = next(section_dir / f["name"] for f in files if f["name"].endswith("_transcripts.parquet.gz"))
    with tempfile.NamedTemporaryFile(suffix=".parquet") as parquet, gzip.open(transcripts, "rb") as compressed:
        shutil.copyfileobj(compressed, parquet)  # GEO's parquet files are gzip-wrapped (CLAUDE.md, Gotchas)
        parquet.flush()
        molecules = pq.ParquetFile(parquet.name).metadata.num_rows
    cells_file = next(section_dir / f["name"] for f in files if f["name"].endswith("_cells.csv.gz"))
    with gzip.open(cells_file, "rt") as cells_csv:
        cells = sum(1 for _ in cells_csv) - 1  # minus the header row
    raw_volume.commit()
    return {
        "section": gsm,
        "section_name": f"x{int(gsm[3:]) - 8720408}",
        "files": files,
        "molecules": molecules,
        "cells": cells,
        "bytes_downloaded": downloaded,
        "seconds": round(time.perf_counter() - started, 2),
    }


@app.local_entrypoint()
def batch(output: str = "") -> None:
    """Fan `fetch_section` out over every section and log the runtime and the estimated compute cost."""
    started = time.perf_counter()
    results = list(fetch_section.map(SECTIONS))
    wall_seconds = time.perf_counter() - started
    container_seconds = sum(r["seconds"] for r in results)
    usd_per_second = BATCH_CPU * CPU_USD_PER_CORE_SECOND + BATCH_MEMORY_MIB / 1024 * MEMORY_USD_PER_GIB_SECOND
    cost = container_seconds * usd_per_second
    for r in results:
        print(f"{r['section']} {r['section_name']:>4}  molecules={r['molecules']:>9,}  cells={r['cells']:>7,}  "
              f"downloaded={r['bytes_downloaded']:>10,} B  {r['seconds']:>6.2f} s")
    by_cells_table: dict[str, list[str]] = {}
    for r in results:
        cells_sha = next(f["sha256"] for f in r["files"] if f["name"].endswith("_cells.csv.gz"))
        by_cells_table.setdefault(cells_sha, []).append(f"{r['section']} ({r['section_name']})")
    duplicates = [sections for sections in by_cells_table.values() if len(sections) > 1]
    summary = {
        "dataset": "GSE286184",
        "sections": len(results),
        "sections_with_identical_cells_tables": duplicates,
        "molecules": sum(r["molecules"] for r in results),
        "cells": sum(r["cells"] for r in results),
        "wall_seconds": round(wall_seconds, 2),
        "container_seconds": round(container_seconds, 2),
        "estimated_cost_usd": round(cost, 6),
        "cost_basis": (f"container seconds x ({BATCH_CPU} core x ${CPU_USD_PER_CORE_SECOND}/core/s + "
                       f"{BATCH_MEMORY_MIB / 1024} GiB x ${MEMORY_USD_PER_GIB_SECOND}/GiB/s), Modal list prices "
                       "2026-11-02; excludes image builds and the minimum billing per container"),
    }
    print(json.dumps({k: v for k, v in summary.items()}, indent=2))
    if output:
        Path(output).write_text(json.dumps({**summary, "per_section": results}, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {output}")
