"""The frozen exclusive marker pairs (`configs/exclusive_marker_pairs.json`) and each gene's home cell type.

The pairs were frozen from the GSE271188 single-nucleus reference before any Xenium evaluation; every audit
result records the artifact's path and the sha256 of its bytes. Home cell types follow the marker map behind
the full-panel label rule.
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from ..contracts import MarkerPairsSource
from ..data.label_rules import MARKERS
from ..settings import _repo_root

FROZEN_MARKER_PAIRS = Path("configs") / "exclusive_marker_pairs.json"

HOME_CELL_TYPES: dict[str, str] = {gene: cell_type for cell_type, genes in MARKERS.items() for gene in genes}
"""A marker gene's home cell type: the cell type it marks in the full-panel rule's marker map."""


@dataclass(frozen=True)
class MarkerPairs:
    pairs: tuple[tuple[str, str], ...]
    source: MarkerPairsSource


def home_cell_type(gene: str) -> str | None:
    return HOME_CELL_TYPES.get(gene)


def load_marker_pairs(path: Path | None = None) -> MarkerPairs:
    """Read a marker-pair artifact; without a path, the frozen one in this checkout."""
    root = _repo_root()
    path = Path(path) if path is not None else root / FROZEN_MARKER_PAIRS
    raw = path.read_bytes()
    data = json.loads(raw)
    pairs = tuple(tuple(sorted(p["genes"])) for p in data["pairs"])
    try:
        shown = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        shown = str(path)
    source = data.get("source", {})
    return MarkerPairs(
        pairs=pairs,  # type: ignore[arg-type]
        source=MarkerPairsSource(
            path=shown,
            sha256=hashlib.sha256(raw).hexdigest(),
            frozen_on=data.get("frozen_on"),
            source_dataset=source.get("dataset"),
            source_url=source.get("url"),
            pair_count=len(pairs),
        ),
    )
