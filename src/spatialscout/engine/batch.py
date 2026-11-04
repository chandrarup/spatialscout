"""Compute the audit results the demo needs on GSE286184 and write them as small committed artifacts.

    uv run spatialscout audit        # or `make audit`; needs `make data` first

Writes `artifacts/GSE286184/audit/`: one JSON audit result per finding, its random-thinning control, the
hero population's label-sensitivity check, one composite figure per result (`figures/`), and `index.json`.
Every section of the dataset is considered; a section duplicating another is listed as left out, never counted.
Nothing here asserts an outcome: the labels are whatever the frozen rules compute.
"""

import hashlib
import json
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..contracts import AuditIndex, AuditIndexEntry, AuditResult, ConditionName, Contract
from ..data import FULL_PANEL_RULE, NPHS1_ANCHORED_RULE, DatasetStore
from ..data.label_rules import MARKERS
from .conditions import PRIMARY_CONDITIONS
from .contrast_batch import section_disclosure
from .controls import label_sensitivity_check, random_thinning_control
from .figure import render_composite_figure
from .markers import FROZEN_MARKER_PAIRS
from .population import Measure, audit_population

DATASET = "GSE286184"


@dataclass(frozen=True)
class Spec:
    slug: str
    title: str
    label_rule_id: str
    cell_type: str
    genes: tuple[str, ...] = ()
    measure: Measure | None = None
    hero: bool = False


def demo_specs() -> list[Spec]:
    """The audit results the demo shows: the hero population under both label rules, the co-expression score per
    cell type, UMOD in immune cells and the podocyte genes one by one."""
    specs = [
        Spec("hero-podocyte-lrp2-cubn", "Podocytes with LRP2 or CUBN (NPHS1-anchored rule)", NPHS1_ANCHORED_RULE, "Podocyte", ("LRP2", "CUBN"), hero=True),
        Spec("hero-podocyte-lrp2-cubn-full-panel", "Podocytes with LRP2 or CUBN (full-panel rule)", FULL_PANEL_RULE, "Podocyte", ("LRP2", "CUBN")),
        Spec("umod-b-cell", "UMOD in B cells", FULL_PANEL_RULE, "B cell", ("UMOD",)),
        Spec("umod-t-cell", "UMOD in T cells", FULL_PANEL_RULE, "T cell", ("UMOD",)),
        Spec("umod-myeloid", "UMOD in myeloid cells", FULL_PANEL_RULE, "Myeloid", ("UMOD",)),
        Spec("podocyte-nphs1", "NPHS1 in podocytes (NPHS1-anchored rule)", NPHS1_ANCHORED_RULE, "Podocyte", ("NPHS1",)),
        Spec("podocyte-lrp2", "LRP2 in podocytes (NPHS1-anchored rule)", NPHS1_ANCHORED_RULE, "Podocyte", ("LRP2",)),
        Spec("podocyte-cubn", "CUBN in podocytes (NPHS1-anchored rule)", NPHS1_ANCHORED_RULE, "Podocyte", ("CUBN",)),
    ]
    for cell_type in MARKERS:
        slug = cell_type.lower().replace(" ", "-").replace("/", "-")
        specs.append(Spec(f"coexpression-{slug}", f"Co-expression score in {cell_type} cells", FULL_PANEL_RULE, cell_type, measure="co_expression_score"))
    return specs


def run_batch(store: DatasetStore, out_dir: Path, repo_root: Path, log: Callable[[str], None] = print,
              specs: Sequence[Spec] | None = None, conditions: Sequence[ConditionName] = PRIMARY_CONDITIONS) -> AuditIndex:
    specs = list(specs or demo_specs())
    infos = store.sections(DATASET)
    counted = [s for s in infos if s.duplicate_of is None]
    left_out = {s.section_id: f"duplicate_of {s.duplicate_of}" for s in infos if s.duplicate_of is not None}
    groups = {s.section_id: s.group for s in counted if s.group}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "controls").mkdir(exist_ok=True)
    disclosure = section_disclosure(store)
    by_rule: dict[str, list] = {}
    for rule in sorted({s.label_rule_id for s in specs}):
        started = time.perf_counter()
        by_rule[rule] = [store.load_section(s.section_id, rule) for s in counted]
        log(f"loaded {len(counted)} sections under {rule} in {time.perf_counter() - started:.1f} s")

    entries: list[AuditIndexEntry] = []
    for spec in specs:
        started = time.perf_counter()
        sections = by_rule[spec.label_rule_id]
        result = audit_population(sections, spec.cell_type, list(spec.genes), conditions, measure=spec.measure,
                                  section_groups=groups, sections_left_out=left_out)
        control = random_thinning_control(result)
        finding_path = f"audit/{spec.slug}.json"
        control_path = f"audit/controls/{spec.slug}-random-thinning.json"
        _write(out_dir.parent / finding_path, result)
        _write(out_dir.parent / control_path, control)
        figure = render_composite_figure(result, {s.section_id: s for s in sections}, out_dir / "figures", title=spec.title, disclosure=disclosure)
        figure = figure.model_copy(update={"path": f"audit/{figure.path}"})
        entry = AuditIndexEntry(
            slug=spec.slug,
            title=spec.title,
            finding_id=result.finding_id,
            finding_path=finding_path,
            label=result.label,
            label_rule_id=spec.label_rule_id,
            cell_type=spec.cell_type,
            genes=result.genes,
            measure=result.measure,
            eligible_sections=len(result.eligible_section_ids),
            figure=figure,
            random_thinning_control_id=control.control_id,
            random_thinning_control_path=control_path,
        )
        if spec.hero:
            check = label_sensitivity_check(
                {NPHS1_ANCHORED_RULE: by_rule[NPHS1_ANCHORED_RULE], FULL_PANEL_RULE: by_rule[FULL_PANEL_RULE]},
                spec.cell_type, list(spec.genes), conditions, section_groups=groups, sections_left_out=left_out,
            )
            check_path = f"audit/controls/{spec.slug}-label-sensitivity.json"
            _write(out_dir.parent / check_path, check)
            entry = entry.model_copy(update={"label_sensitivity_control_id": check.control_id, "label_sensitivity_control_path": check_path})
            log(f"  label-sensitivity check: {check.summary}")
        entries.append(entry)
        log(f"{spec.slug}: {result.label.value} ({len(result.eligible_section_ids)} eligible sections) in {time.perf_counter() - started:.1f} s")

    inputs = [FROZEN_MARKER_PAIRS, Path("artifacts") / DATASET / "label_rules.json", Path("artifacts") / DATASET / "manifest.json"]
    index = AuditIndex(
        dataset_id=DATASET,
        generated_by="spatialscout audit (src/spatialscout/engine/batch.py)",
        sections_counted=[s.section_id for s in counted],
        sections_left_out=[{"section_id": k, "reason": v} for k, v in sorted(left_out.items())],
        input_sha256={p.as_posix(): hashlib.sha256((repo_root / p).read_bytes()).hexdigest() for p in inputs},
        entries=entries,
        section_disclosure=disclosure,
    )
    _write(out_dir / "index.json", index)
    return index


def _write(path: Path, model: Contract) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(model.model_dump(mode="json"), indent=1, allow_nan=False) + "\n", encoding="utf-8")


__all__ = ["AuditResult", "Spec", "demo_specs", "run_batch"]
