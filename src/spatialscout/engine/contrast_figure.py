"""Render a contrast result's composite figure as a PNG.

- Panel A: each section's log2(CP10K + 1) value by group and condition, labelled `group (n=k)`, with group means;
  the exploratory structure-constrained condition sits in its own shaded column and never enters the label.
- Panel B: a 300 x 300 µm tissue crop around the top evidence region (shared with the audit figure).
"""

import hashlib
import io
from collections.abc import Mapping
from pathlib import Path
from types import SimpleNamespace

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from ..contracts import CompositeFigure, ConditionName, ContrastResult, content_id  # noqa: E402
from ..data import SectionTables  # noqa: E402
from .figure import CONDITION_LABELS, _panel_b  # noqa: E402

GROUP_COLOURS = ("#1f5fbf", "#c2185b")
EXPLORATORY_LABEL = "structure-\nconstrained\n(SAM 3.1 proposal,\nexploratory)"


def render_contrast_figure(result: ContrastResult, sections: Mapping[str, SectionTables], out_dir: Path, *, title: str) -> CompositeFigure:
    figure, (panel_a, panel_b) = plt.subplots(1, 2, figsize=(13, 5.6), gridspec_kw={"width_ratios": [1.25, 1]})
    figure.suptitle(
        f"{title}\nEvidence label: {result.label.value.replace('_', ' ')} · descriptive only, no p-values"
        + (f"\n{result.section_disclosure}" if result.section_disclosure else ""),
        fontsize=9.5,
    )
    a_text = _panel_a(panel_a, result)
    region = next((r for r in result.evidence_regions if r.rank == 1), None)
    crop = None
    if region is not None and region.region.section_id in sections:
        shim = SimpleNamespace(roi=None, population=result.population, genes=[result.gene], measure="share_expressing",
                               evidence_regions=result.evidence_regions)
        crop, b_text = _panel_b(panel_b, shim, sections[region.region.section_id], region.region, 1)
    else:
        panel_b.axis("off")
        b_text = "No evidence region: no molecules of the gene in the population are excluded."
        panel_b.text(0.5, 0.5, "B  " + b_text, ha="center", va="center", fontsize=10, wrap=True)
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
        evidence_rank=1 if crop else None,
        panel_a=a_text,
        panel_b=b_text,
    )


def _panel_a(axis, result: ContrastResult) -> str:
    primary = [e.condition for e in result.effects]
    exploratory = [e.condition for e in result.exploratory_effects]
    columns = primary + exploratory
    xs = {c: i for i, c in enumerate(columns)}
    groups = (result.groups.control, result.groups.disease)
    counts = {g: sum(1 for s in result.sections if s.group == g) for g in groups}
    offsets = (-0.15, 0.15)
    for g, colour, offset in zip(groups, GROUP_COLOURS, offsets, strict=True):
        label_done = False
        for values in (result.per_section, result.exploratory_per_section):
            rows = [v for v in values if v.group == g and v.log2_value is not None and v.condition in xs]
            if not rows:
                continue
            axis.scatter([xs[v.condition] + offset for v in rows], [v.log2_value for v in rows], s=16, color=colour, alpha=0.75,
                         label=None if label_done else f"{g} (n={counts[g]})")
            label_done = True
            for c in {v.condition for v in rows}:
                mean = float(np.mean([v.log2_value for v in rows if v.condition == c]))
                axis.plot([xs[c] + offset - 0.1, xs[c] + offset + 0.1], [mean, mean], color=colour, linewidth=2.2)
    if exploratory:
        start = len(primary) - 0.5
        axis.axvspan(start, len(columns) - 0.5, color="#f5c518", alpha=0.12)
    valid = set(result.valid_conditions)
    names = [CONDITION_LABELS.get(c, c.value) + ("" if c in valid else "\n(invalid)") for c in primary] + [EXPLORATORY_LABEL] * len(exploratory)
    axis.set_xticks(range(len(columns)), names, fontsize=8)
    for effect in [*result.effects, *result.exploratory_effects]:
        text = "effect n/a" if effect.effect is None else f"effect {effect.effect:+.2f}"
        if effect.condition in exploratory:
            used = [v for v in result.exploratory_per_section if v.condition == effect.condition]
            text += "\n" + " vs ".join(f"{g} n={sum(1 for v in used if v.group == g)}" for g in (result.groups.disease, result.groups.control))
        axis.annotate(text, (xs[effect.condition], 0), xycoords=("data", "axes fraction"), xytext=(0, 4),
                      textcoords="offset points", ha="center", fontsize=7.5, color="#555555")
    axis.set_ylabel(f"{result.gene} in {result.population.cell_type} cells, log2(CP10K + 1)")
    axis.set_title(f"A  Per-section values by group and condition ({result.groups.disease} vs {result.groups.control})", fontsize=10, loc="left")
    axis.legend(fontsize=8, loc="upper right", frameon=False)
    axis.spines[["top", "right"]].set_visible(False)
    explo = " The structure-constrained column is an exploratory SAM 3.1 proposal on sections with outlines only; it never sets the label." if exploratory else ""
    return (
        f"Per-section log2(CP10K + 1) of {result.gene} in {result.population.cell_type} cells for "
        + ", ".join(f"{g} (n={counts[g]})" for g in groups)
        + f" under {', '.join(CONDITION_LABELS.get(c, c.value) for c in primary)}, with group means and the effect per condition.{explo}"
    )


__all__ = ["render_contrast_figure", "ConditionName"]
