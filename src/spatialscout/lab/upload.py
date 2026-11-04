"""Bring your own sections: audit Xenium output the researcher uploads (or links), with the same engine as the
built-in dataset, and nothing kept.

Each section is a standard Xenium pair: `transcripts.parquet` (or `.csv`, optionally gzipped) and `cells.csv` (or
`.parquet`, optionally gzipped). The upload sits in temporary storage (memory, or a temporary file for large
parts) that is deleted when the request ends; the figure is drawn in a temporary directory deleted at once. Nothing
is stored and no model is called, so no part of the data leaves this server. The same validation, frozen label rules (with GSE286184's pooled gene scales) and audit as GSE286184 run on
them, and the publication figure is returned inline.

Label rules are frozen on GSE286184's 50-gene panel markers: a panel without those markers leaves cells unlabelled, and
the result says so. An audit result needs at least three eligible sections, as everywhere else."""

import base64
import gzip
import io
import json
import tempfile
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from ..contracts import AuditResult, Contract, SectionValidation
from ..data.label_rules import FULL_PANEL_RULE, apply_label_rules
from ..data.tables import make_section
from ..data.validation import validate_section
from ..engine.population import audit_population
from . import figures

MAX_BYTES = 40 * 1024 * 1024  # per request: the web container has 1 GB of memory
DATASET_ID = "uploaded"


class UploadedSectionSummary(Contract):
    section_id: str
    validation: SectionValidation
    cell_types: dict[str, int]


class UploadAudit(Contract):
    """The audit of the uploaded sections. `retained` is always false: the files are deleted when the request ends."""

    sections: list[UploadedSectionSummary]
    result: AuditResult | None
    problem: str | None = None
    figure_svg: str | None = None
    figure_png_base64: str | None = None
    legend: str | None = None
    retained: bool = False
    handling: str


HANDLING = (
    "Held in temporary storage for this request only and deleted when it ends. Nothing is stored or sent to a model; "
    "the audit and the figure are computed on this server and returned only to you, over HTTPS."
)


def read_table(name: str, data: bytes) -> pd.DataFrame:
    if len(data) > MAX_BYTES:
        raise ValueError(f"{name} is over the {MAX_BYTES // 2**20} MB limit")
    lower = name.lower()
    if lower.endswith(".gz"):
        data = gzip.decompress(data)
        lower = lower[:-3]
    if lower.endswith(".parquet"):
        return pd.read_parquet(io.BytesIO(data))
    if lower.endswith(".csv"):
        return pd.read_csv(io.BytesIO(data))
    raise ValueError(f"{name}: expected .parquet or .csv (optionally .gz)")


def gene_scales(artifacts_dir: Path) -> dict[str, float]:
    rules = json.loads((artifacts_dir / "GSE286184" / "label_rules.json").read_text(encoding="utf-8"))
    return {k: float(v) for k, v in rules["gene_scales"].items()}


def audit_upload(
    pairs: Sequence[tuple[str, pd.DataFrame, pd.DataFrame]],
    *,
    cell_type: str,
    genes: Sequence[str],
    scales: dict[str, float],
    label_rule_id: str = FULL_PANEL_RULE,
) -> UploadAudit:
    """`pairs`: (section name, transcripts, cells) per uploaded section."""
    sections, summaries = [], []
    for name, transcripts, cells in pairs:
        panel = sorted(set(transcripts["feature_name"].astype(str)))
        validated = validate_section(transcripts, cells, panel)
        labels = apply_label_rules(validated.molecules, validated.cells["cell_id"].tolist(), scales)
        table = validated.cells.copy()
        table["cell_type"] = labels[label_rule_id].reindex(table["cell_id"]).to_numpy()
        sections.append(make_section(name, DATASET_ID, label_rule_id, validated.molecules, table))
        summaries.append(UploadedSectionSummary(section_id=name, validation=validated.validation,
                                                cell_types={str(k): int(v) for k, v in table["cell_type"].value_counts().items()}))
    try:
        result = audit_population(sections, cell_type, list(genes))
    except ValueError as error:
        return UploadAudit(sections=summaries, result=None, problem=str(error), handling=HANDLING)
    with tempfile.TemporaryDirectory(prefix="spatialscout-figure-") as tmp:
        svg, _, png, legend, _, _ = figures.render(result, Path(tmp), "uploaded")
        svg_text = (Path(tmp) / svg).read_text(encoding="utf-8")
        png_b64 = base64.b64encode((Path(tmp) / png).read_bytes()).decode()
    return UploadAudit(sections=summaries, result=result, figure_svg=svg_text, figure_png_base64=png_b64, legend=legend, handling=HANDLING)
