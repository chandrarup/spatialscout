"""Compute every descriptive disease contrast on GSE286184 and write them as small committed artifacts.

    uv run spatialscout contrasts    # or `make contrasts`; needs `make data` first

Writes `artifacts/GSE286184/contrasts/`: one JSON contrast result per (contrast, label rule, cell type, gene), one
composite figure each (`figures/`), and `index.json` with the run configuration (the frozen rules, conditions and
the grid, all fixed before computing), the GEO citation and the input checksums. A duplicate section is listed as
left out, never counted. Nothing here asserts an outcome: the labels are whatever the frozen rules compute.
"""

import hashlib
import json
import time
from collections.abc import Callable
from pathlib import Path

from ..contracts import ConditionName, ContrastIndex, ContrastIndexEntry, ContrastRunConfiguration, Contract, LeftOutSection
from ..data import FULL_PANEL_RULE, NPHS1_ANCHORED_RULE, DatasetStore
from ..data.label_rules import MARKERS
from .conditions import EXPLORATORY_CONDITIONS, PRIMARY_CONDITIONS
from .contrast import compute_contrast, contrast_rules
from .contrast_figure import render_contrast_figure

DATASET = "GSE286184"
CONDITIONS: tuple[ConditionName, ...] = (*PRIMARY_CONDITIONS, *EXPLORATORY_CONDITIONS)


def contrast_grid() -> list[tuple[str, str, str]]:
    """(label rule, cell type, gene), fixed before computing: the podocyte genes of the hero question under the
    NPHS1-anchored rule, each other cell type's own markers under the full-panel rule, and UMOD in immune cells."""
    grid = [(NPHS1_ANCHORED_RULE, "Podocyte", g) for g in ("NPHS1", "LRP2", "CUBN")]
    grid += [(FULL_PANEL_RULE, cell_type, gene) for cell_type, genes in MARKERS.items() if cell_type != "Podocyte" for gene in genes]
    grid += [(FULL_PANEL_RULE, cell_type, "UMOD") for cell_type in ("T cell", "B cell", "Myeloid")]
    return grid


def section_disclosure(store: DatasetStore) -> str:
    """'22 sections from 19 donors', from the manifest and the published donor counts in the capability report."""
    infos = store.sections(DATASET)
    report = store.capability_report(DATASET)
    donors = {c.groups.control: c.control_donors_published for c in report.contrasts}
    donors |= {c.groups.disease: c.disease_donors_published for c in report.contrasts}
    distinct = [s for s in infos if s.duplicate_of is None]
    duplicates = [f"{s.section_id} duplicates {s.duplicate_of}" for s in infos if s.duplicate_of is not None]
    return (
        f"{len(infos)} sections from {sum(donors.values())} donors (published counts; GEO does not map sections to donors), "
        f"{len(distinct)} distinct" + (f" ({'; '.join(duplicates)})" if duplicates else "") + ". Sections are not independent donors."
    )


def _slug(*parts: str) -> str:
    return "-".join(p.lower().replace(" ", "-").replace("/", "-") for p in parts)


def run_contrasts(store: DatasetStore, out_dir: Path, repo_root: Path, log: Callable[[str], None] = print) -> ContrastIndex:
    infos = store.sections(DATASET)
    counted = [s for s in infos if s.duplicate_of is None]
    left_out = {s.section_id: f"duplicate_of {s.duplicate_of}" for s in infos if s.duplicate_of is not None}
    groups = {s.section_id: s.group for s in counted if s.group}
    report = store.capability_report(DATASET)
    disclosure = section_disclosure(store)
    grid = contrast_grid()
    out_dir.mkdir(parents=True, exist_ok=True)

    by_rule = {}
    for rule in sorted({r for r, _, _ in grid}):
        started = time.perf_counter()
        by_rule[rule] = [store.load_section(s.section_id, rule) for s in counted]
        log(f"loaded {len(counted)} sections under {rule} in {time.perf_counter() - started:.1f} s")

    entries: list[ContrastIndexEntry] = []
    for eligibility in report.contrasts:
        contrast = eligibility.groups
        for rule, cell_type, gene in grid:
            started = time.perf_counter()
            sections = by_rule[rule]
            result = compute_contrast(
                sections, groups, contrast, cell_type, gene, CONDITIONS,
                inference_reason=eligibility.inference_reason, donor_distinctness=eligibility.donor_distinctness,
                sections_left_out={k: v for k, v in left_out.items() if groups.get(k) is None and _group_of(infos, k) in (contrast.disease, contrast.control)},
                section_disclosure=disclosure,
            )
            slug = _slug(contrast.disease, "vs", contrast.control, cell_type, gene, rule)
            finding_path = f"contrasts/{slug}.json"
            _write(out_dir.parent / finding_path, result)
            title = f"{gene} in {cell_type} cells, {contrast.disease} vs {contrast.control} ({rule})"
            figure = render_contrast_figure(result, {s.section_id: s for s in sections}, out_dir / "figures", title=title)
            figure = figure.model_copy(update={"path": f"contrasts/{figure.path}"})
            entries.append(ContrastIndexEntry(
                slug=slug, title=title, finding_id=result.finding_id, finding_path=finding_path, groups=contrast,
                label=result.label, label_rule_id=rule, cell_type=cell_type, gene=gene,
                disease_sections=sum(1 for s in result.sections if s.group == contrast.disease),
                control_sections=sum(1 for s in result.sections if s.group == contrast.control),
                donor_distinctness=result.donor_distinctness, figure=figure,
            ))
            log(f"{slug}: {result.label.value} in {time.perf_counter() - started:.1f} s")

    inputs = [Path("artifacts") / DATASET / "label_rules.json", Path("artifacts") / DATASET / "manifest.json",
              Path("artifacts") / DATASET / "capability_report.json"]
    inputs += sorted(Path("artifacts") / DATASET / "structures" / p.name for p in (repo_root / "artifacts" / DATASET / "structures").glob("*.json"))
    index = ContrastIndex(
        dataset_id=DATASET,
        generated_by="spatialscout contrasts (src/spatialscout/engine/contrast_batch.py)",
        citation=store.manifest(DATASET).citation,
        section_disclosure=disclosure,
        sections_counted=[s.section_id for s in counted],
        sections_left_out=[LeftOutSection(section_id=k, reason=v) for k, v in sorted(left_out.items())],
        input_sha256={p.as_posix(): hashlib.sha256((repo_root / p).read_bytes()).hexdigest() for p in inputs},
        run_configuration=ContrastRunConfiguration(
            rules=contrast_rules(" + ".join(sorted({r for r, _, _ in grid}))),
            conditions=list(CONDITIONS),
            grid=[list(g) for g in grid],
            contrasts=[c.groups for c in report.contrasts],
        ),
        entries=entries,
    )
    _write(out_dir / "index.json", index)
    current = {Path(e.figure.path).name for e in entries if e.figure}
    for stale in (out_dir / "figures").glob("*.png"):
        if stale.name not in current:
            stale.unlink()
    return index


def _group_of(infos, section_id: str) -> str | None:
    return next((s.group for s in infos if s.section_id == section_id), None)


def _write(path: Path, model: Contract) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(model.model_dump(mode="json"), indent=1, allow_nan=False) + "\n", encoding="utf-8")


__all__ = ["contrast_grid", "run_contrasts", "section_disclosure"]
