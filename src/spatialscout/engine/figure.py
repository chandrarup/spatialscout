"""Render an audit result's composite figure as a PNG.

- Panel A: the observed value of each eligible section across conditions (thin lines), the pooled observed value,
  and both pooled random-thinning expectations, with the frozen threshold (home-matched x 2^-0.5).
- Panel B: a 300 x 300 µm crop centred on an evidence region: nuclei by cell type (population and home type
  emphasised), the result's retained molecules, and its excluded molecules in yellow.
"""

import hashlib
import io
from collections.abc import Mapping
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.collections import PatchCollection  # noqa: E402
from matplotlib.patches import Circle, Rectangle  # noqa: E402

from ..contracts import AuditResult, CompositeFigure, ConditionName, Region, content_id  # noqa: E402
from ..data import SectionTables  # noqa: E402
from .markers import HOME_CELL_TYPES  # noqa: E402
from .population import THRESHOLD_FACTOR, _index, restrict_to_roi  # noqa: E402

CROP_UM = 300.0
EXCLUDED = "#f5c518"
RETAINED = "#1f5fbf"
POPULATION = "#c2185b"
HOME = "#2e7d32"
OTHER = "#9e9e9e"
CONDITION_LABELS = {
    ConditionName.DEFAULT: "default",
    ConditionName.NUCLEUS_ONLY: "nucleus-only",
    ConditionName.DISTANCE_CAP_1UM: "cap 1 µm",
    ConditionName.DISTANCE_CAP_2UM: "cap 2 µm",
}


def render_composite_figure(
    result: AuditResult,
    sections: Mapping[str, SectionTables],
    out_dir: Path,
    *,
    title: str,
    rank: int = 1,
    disclosure: str | None = None,
) -> CompositeFigure:
    """Write `<finding_id>.png` into `out_dir` and describe it. `sections` holds the section of the evidence
    region (under the result's label rule)."""
    figure, (panel_a, panel_b) = plt.subplots(1, 2, figsize=(12, 5.2), gridspec_kw={"width_ratios": [1.15, 1]})
    figure.suptitle(f"{title}\nEvidence label: {result.label.value.replace('_', ' ')}" + (f"\n{disclosure}" if disclosure else ""),
                    fontsize=11 if not disclosure else 9.5)
    a_text = _panel_a(panel_a, result)
    region = next((r for r in result.evidence_regions if r.rank == rank), None)
    crop = None
    if region is not None and region.region.section_id in sections:
        crop, b_text = _panel_b(panel_b, result, sections[region.region.section_id], region.region, rank)
    else:
        panel_b.axis("off")
        panel_b.text(0.5, 0.5, "B  No evidence region: no molecules of the result are excluded.", ha="center", va="center", fontsize=10)
        b_text = "No evidence region: no molecules of the result are excluded."
    figure.tight_layout()
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", dpi=100)
    plt.close(figure)
    png = buffer.getvalue()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{result.finding_id}.png"
    path.write_bytes(png)
    sha = hashlib.sha256(png).hexdigest()
    return CompositeFigure(
        figure_id=content_id("fig", {"finding_id": result.finding_id, "sha256": sha}),
        finding_id=result.finding_id,
        path=f"figures/{path.name}",
        sha256=sha,
        crop=crop,
        evidence_rank=rank if crop else None,
        panel_a=a_text,
        panel_b=b_text,
    )


def _panel_a(axis, result: AuditResult) -> str:
    conditions = [c for c in CONDITION_LABELS if any(p.condition == c for p in result.pooled)] or [ConditionName.DEFAULT]
    xs = np.arange(len(conditions))
    eligible = set(result.eligible_section_ids)
    shown = [s for s in result.sections if s.section_id in eligible] or result.sections
    for section in shown:
        by = {v.condition: v.observed_value for v in section.conditions}
        ys = [by.get(c) for c in conditions]
        axis.plot(xs, [np.nan if y is None else y for y in ys], color=OTHER, linewidth=0.8, alpha=0.6, marker="o", markersize=2.5)
    pooled = {p.condition: p for p in result.pooled}
    if pooled and result.eligible_section_ids:
        get = lambda name: [np.nan if getattr(pooled[c], name) is None else getattr(pooled[c], name) for c in conditions]  # noqa: E731
        home = get("expectation_home_matched")
        axis.plot(xs, get("observed_value"), color="black", linewidth=2.2, marker="o", label="observed (pooled)")
        axis.plot(xs, home, color=HOME, linestyle="--", linewidth=1.8, label="home-matched expectation")
        axis.plot(xs, get("expectation_cell_matched"), color=RETAINED, linestyle=":", linewidth=1.8, label="cell-matched expectation")
        axis.plot(xs, [h * THRESHOLD_FACTOR for h in home], color=HOME, linestyle="-", linewidth=0.8, alpha=0.5, label="threshold: home x 2^-0.5")
        for x, c in zip(xs, conditions, strict=True):
            retention = pooled[c].retention
            axis.annotate(f"retention {retention:.0%}" if retention is not None else "retention n/a", (x, 0), xytext=(0, -26),
                          textcoords="offset points", ha="center", fontsize=7.5, color="#555555", annotation_clip=False)
    axis.plot([], [], color=OTHER, linewidth=0.8, label=f"each section (n = {len(shown)})")
    axis.set_xticks(xs, [CONDITION_LABELS[c] for c in conditions])
    axis.set_ylim(bottom=0)
    measure = {"share_expressing": "share of cells expressing", "gene_set_share_expressing": "share of cells expressing any gene",
               "co_expression_score": "co-expression score"}[result.measure]
    axis.set_ylabel(measure)
    scope = f"{len(result.eligible_section_ids)} eligible of {len(result.sections)} sections"
    axis.set_title(f"A  Observed vs random-thinning expectations ({scope})", fontsize=10, loc="left")
    axis.legend(fontsize=7.5, loc="upper right", frameon=False)
    axis.spines[["top", "right"]].set_visible(False)
    return (
        f"Per-section observed {measure} across {', '.join(CONDITION_LABELS[c] for c in conditions)} for {scope}, with the "
        "pooled observed value and the pooled home-matched and cell-matched expectations."
    )


def _panel_b(axis, result: AuditResult, section: SectionTables, region: Region, rank: int) -> tuple[Region, str]:
    if result.roi is not None:
        section = restrict_to_roi(section, result.roi)
    cx, cy = (region.x0 + region.x1) / 2, (region.y0 + region.y1) / 2
    crop = Region(section_id=region.section_id, x0=cx - CROP_UM / 2, y0=cy - CROP_UM / 2, x1=cx + CROP_UM / 2, y1=cy + CROP_UM / 2)
    index = _index(section)
    cell_type = result.population.cell_type
    homes = {HOME_CELL_TYPES.get(g) for g in result.genes} - {None, cell_type}
    in_crop = lambda x, y: (x >= crop.x0) & (x <= crop.x1) & (y >= crop.y0) & (y <= crop.y1)  # noqa: E731

    cells = section.cells
    radius = np.sqrt(np.nan_to_num(cells["nucleus_area"].to_numpy(dtype=float), nan=0.0) / np.pi)
    types = cells["cell_type"].astype(str).to_numpy()
    visible = np.flatnonzero(in_crop(index.cell_x, index.cell_y))
    for kind, colour, width in (("other", OTHER, 0.5), ("home", HOME, 1.1), ("population", POPULATION, 1.4)):
        chosen = [i for i in visible if (types[i] == cell_type) == (kind == "population") and ((types[i] in homes) == (kind == "home"))]
        patches = [Circle((index.cell_x[i], index.cell_y[i]), max(radius[i], 1.0)) for i in chosen]
        axis.add_collection(PatchCollection(patches, facecolor="none", edgecolor=colour, linewidth=width, alpha=0.9 if kind != "other" else 0.5))

    genes = [index.gene_code(g) for g in result.genes]
    result_genes = [g for g, name in zip(genes, result.genes, strict=True) if g >= 0 and (result.measure != "co_expression_score" or HOME_CELL_TYPES.get(name) != cell_type)]
    molecules = in_crop(index.x, index.y)
    condition = next(r.condition for r in result.evidence_regions if r.rank == rank) or ConditionName.NUCLEUS_ONLY
    default, kept = index.mask(ConditionName.DEFAULT), index.mask(condition)
    population_cell = np.zeros(len(index.cell_x), dtype=bool)
    population_cell[index.type_codes == index.type_code(cell_type)] = True
    in_population = (index.cell_codes >= 0) & population_cell[np.clip(index.cell_codes, 0, None)]
    of_result = np.isin(index.gene_codes, result_genes)
    scope = molecules & default & in_population & of_result
    background = molecules & ~scope
    axis.scatter(index.x[background], index.y[background], s=0.6, color="#cfcfcf", linewidths=0)
    retained, excluded = scope & kept, scope & ~kept
    axis.scatter(index.x[retained], index.y[retained], s=9, color=RETAINED, linewidths=0, label=f"retained ({int(retained.sum())})")
    axis.scatter(index.x[excluded], index.y[excluded], s=14, color=EXCLUDED, edgecolors="#7a5c00", linewidths=0.4,
                 label=f"excluded under {CONDITION_LABELS.get(condition, condition.value)} ({int(excluded.sum())})")
    axis.add_patch(Rectangle((region.x0, region.y0), region.x1 - region.x0, region.y1 - region.y0, fill=False, edgecolor="black",
                             linestyle="--", linewidth=0.8))
    axis.plot([], [], color=POPULATION, label=f"{cell_type} nuclei")
    if homes:
        axis.plot([], [], color=HOME, label=f"home type nuclei ({', '.join(sorted(homes))})")
    axis.set_xlim(crop.x0, crop.x1)
    axis.set_ylim(crop.y1, crop.y0)
    axis.set_aspect("equal")
    axis.set_xlabel("x (µm)")
    axis.set_ylabel("y (µm)")
    gene_text = "/".join(result.genes) if result.measure != "co_expression_score" else "foreign marker"
    axis.set_title(f"B  Evidence region rank {rank}, {region.section_id}\n{gene_text} molecules in {cell_type} cells (300 µm crop)",
                   fontsize=10, loc="left")
    axis.legend(fontsize=7.5, loc="upper right", framealpha=0.85)
    axis.text(0.01, 0.01, "Nuclei drawn as circles of each nucleus's area (approximation)", transform=axis.transAxes, fontsize=6.5, color="#555555")
    return crop, (
        f"300 x 300 µm crop of {region.section_id} around evidence region rank {rank}: {int(retained.sum())} retained and "
        f"{int(excluded.sum())} excluded (yellow) molecules of the result in {cell_type} cells under {condition.value}."
    )
