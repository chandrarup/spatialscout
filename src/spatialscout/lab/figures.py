"""Publication figures for the lab: a vector figure (SVG and PDF, with a 300 dpi PNG for the browser) of one audit
result at a two-column journal width (180 mm), with panel letters, units, n and a legend written from the computed
numbers. A new artifact beside the composite figure Muse Spark read, which it never replaces.

Panel a: each eligible section's observed value under each assignment condition (grey), the pooled value (black)
and the pooled home-matched random-thinning expectation (dashed). Panel b: each section's change from the default
condition to nucleus-only against the change random thinning alone predicts for it, so a section below the diagonal
lost more than thinning explains. The spread shown is the sections' own; no interval is invented."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from ..contracts import AuditResult, ConditionName  # noqa: E402
from ..engine.figure import CONDITION_LABELS  # noqa: E402

MM = 1 / 25.4
WIDTH_MM = 180
HEIGHT_MM = 78
STYLE = {
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 7,
    "axes.titlesize": 7.5,
    "axes.labelsize": 7,
    "xtick.labelsize": 6.5,
    "ytick.labelsize": 6.5,
    "legend.fontsize": 6,
    "axes.linewidth": 0.6,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "svg.fonttype": "none",
    "pdf.fonttype": 42,
}
MEASURE = {"share_expressing": "Share of cells expressing (%)", "gene_set_share_expressing": "Share of cells expressing any gene (%)",
           "co_expression_score": "Co-expression score"}


def _pct(v: float | None) -> str:
    return "n/a" if v is None else f"{v * 100:.1f}%"


def render(result: AuditResult, out_dir: Path, stem: str) -> tuple[str, str, str, str, int, int]:
    """Writes `<stem>.svg`, `.pdf` and `.png` into out_dir. Returns their names, the legend, the sections and the cells."""
    scale = 100.0 if result.measure != "co_expression_score" else 1.0
    conditions = [c for c in CONDITION_LABELS if any(p.condition == c for p in result.pooled)] or [ConditionName.DEFAULT]
    eligible = set(result.eligible_section_ids)
    sections = [s for s in result.sections if s.section_id in eligible]
    pooled = {p.condition: p for p in result.pooled}
    xs = np.arange(len(conditions))
    genes = "/".join(result.genes) if len(result.genes) <= 3 else f"{len(result.genes)}-gene panel"
    with plt.rc_context(STYLE):
        fig, (a, b) = plt.subplots(1, 2, figsize=(WIDTH_MM * MM, HEIGHT_MM * MM), gridspec_kw={"width_ratios": [1.35, 1]})
        for s in sections:
            by = {v.condition: v.observed_value for v in s.conditions}
            a.plot(xs, [np.nan if by.get(c) is None else by[c] * scale for c in conditions], color="#b8b8b8", linewidth=0.6, marker="o", markersize=1.8, zorder=1)
        if pooled:
            obs = [np.nan if pooled[c].observed_value is None else pooled[c].observed_value * scale for c in conditions]
            exp = [np.nan if pooled[c].expectation_home_matched is None else pooled[c].expectation_home_matched * scale for c in conditions]
            a.plot(xs, obs, color="black", linewidth=1.4, marker="o", markersize=3, label="Observed, pooled", zorder=3)
            a.plot(xs, exp, color="#2e7d32", linewidth=1.1, linestyle="--", label="Random-thinning expectation, pooled", zorder=2)
        a.plot([], [], color="#b8b8b8", linewidth=0.6, marker="o", markersize=1.8, label=f"Single section (n = {len(sections)})")
        a.set_xticks(xs, [CONDITION_LABELS[c] for c in conditions])
        a.set_xlabel("Molecule-to-cell assignment rule")
        a.set_ylabel(MEASURE[result.measure])
        a.set_ylim(bottom=0)
        a.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, borderaxespad=0.2, handlelength=1.6)
        a.spines[["top", "right"]].set_visible(False)
        a.text(-0.12, 1.12, "a", transform=a.transAxes, fontsize=9, fontweight="bold")

        dx, dy = [], []
        for s in sections:
            by = {v.condition: v for v in s.conditions}
            d, n = by.get(ConditionName.DEFAULT), by.get(ConditionName.NUCLEUS_ONLY)
            if d and n and d.observed_value is not None and n.observed_value is not None and n.expectation_home_matched is not None:
                dx.append((n.expectation_home_matched - d.observed_value) * scale)
                dy.append((n.observed_value - d.observed_value) * scale)
        if dx:
            lo = min(min(dx), min(dy), 0) * 1.15 - 0.5
            hi = max(max(dx), max(dy), 0) * 1.15 + 0.5
            b.plot([lo, hi], [lo, hi], color="#2e7d32", linestyle="--", linewidth=0.8, label="Random thinning alone")
            b.axhline(0, color="#d0d0d0", linewidth=0.5, zorder=0)
            b.axvline(0, color="#d0d0d0", linewidth=0.5, zorder=0)
            b.scatter(dx, dy, s=10, color="black", zorder=3, label=f"Section (n = {len(dx)})")
            b.set_xlim(lo, hi)
            b.set_ylim(lo, hi)
            b.set_aspect("equal", adjustable="box")
            b.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, borderaxespad=0.2, handlelength=1.6)
        b.set_xlabel("Expected change, default → nucleus-only (pts)")
        b.set_ylabel("Observed change (pts)")
        b.spines[["top", "right"]].set_visible(False)
        b.text(-0.22, 1.12, "b", transform=b.transAxes, fontsize=9, fontweight="bold")
        fig.tight_layout(w_pad=2.5)
        out_dir.mkdir(parents=True, exist_ok=True)
        names = (f"{stem}.svg", f"{stem}.pdf", f"{stem}.png")
        fig.savefig(out_dir / names[0])
        fig.savefig(out_dir / names[1])
        fig.savefig(out_dir / names[2], dpi=300)
        plt.close(fig)

    d, n = pooled.get(ConditionName.DEFAULT), pooled.get(ConditionName.NUCLEUS_ONLY)
    cells = d.cells if d else 0
    below = sum(1 for x, y in zip(dx, dy, strict=True) if y < x)
    legend = (
        f"{genes} in cells labelled {result.population.cell_type} (label rule {result.population.label_rule_id}), "
        f"{result.dataset_id}, {len(sections)} eligible sections, {cells:,} cells. "
        f"(a) {MEASURE[result.measure].replace(' (%)', '')} under each assignment rule; grey lines are single sections, black is "
        f"pooled ({_pct(d.observed_value if d else None)} default, {_pct(n.observed_value if n else None)} nucleus-only), dashed is the "
        f"pooled expectation if nucleus-only only removed molecules at random ({_pct(n.expectation_home_matched if n else None)}). "
        f"(b) Per section, observed against expected change from default to nucleus-only, in percentage points; "
        f"{below} of {len(dx)} sections fall below the diagonal (lost more than thinning explains). "
        f"Evidence label: {result.label.value.replace('_', ' ')}. Finding {result.finding_id}."
    )
    return *names, legend, len(sections), cells
