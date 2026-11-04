"""The error injector: labelled injected errors derived from a real claim, one pure function per kind.

Each variant changes a structured or cited field and the text together, so the diff shows what changed, and is
always marked `injected.is_injected` with its kind. Nothing here knows or asserts whether the verifier will catch it.
"""

import re
from collections.abc import Callable
from typing import Any

from ..contracts import AuditResult, CitedNumber, Claim, ClaimControls, FieldChange, InjectedError, InjectedErrorKind, VerificationStatus
from .checks import evidence_section, pattern_of, stated_direction

WRONG_DATASET = "GSE271188"  # the frozen single-nucleus reference: a real dataset, but not one any audit claim is about
EFFECT_SHIFT = 0.08

_REVERSALS = (
    ("persists", "drops"), ("persist", "drop"), ("remains at or above", "falls below"), ("remained at or above", "fell below"),
    ("remain at or above", "fall below"), ("stays at or above", "falls below"), ("stayed at or above", "fell below"),
    ("at or above", "below"), ("holds", "drops"), ("remained", "dropped"), ("remains", "drops"),
    ("no condition dropping below", "a condition dropping below"), ("no condition falls below", "a condition falls below"),
)


def inject(kind: InjectedErrorKind, base: Claim, finding: AuditResult, *, other_figure_id: str | None = None) -> tuple[Claim, list[FieldChange]]:
    """The variant of `base` carrying one injected error of `kind`, and the fields it changed."""
    variant = _INJECTORS[kind](base, finding, other_figure_id)
    variant = variant.model_copy(
        update={"claim_id": f"{base.claim_id}-inj-{kind.value}", "injected": InjectedError(is_injected=True, kind=kind),
                "verification_status": VerificationStatus.PENDING}
    )
    return variant, diff(base, variant)


def diff(before: Claim, after: Claim) -> list[FieldChange]:
    a, b = before.model_dump(mode="json"), after.model_dump(mode="json")
    changes = []
    for field in ("dataset_id", "text", "direction", "neighbour_pattern", "figure_id", "controls"):
        if a[field] != b[field]:
            changes.append(FieldChange(field=field, before=a[field], after=b[field]))
    for name in sorted(set(a["cited"]) | set(b["cited"])):
        if a["cited"].get(name) != b["cited"].get(name):
            changes.append(FieldChange(field=f"cited.{name}", before=a["cited"].get(name), after=b["cited"].get(name)))
    return changes


def _reversed_direction(base: Claim, finding: AuditResult, _: Any) -> Claim:
    current = stated_direction(base) or "holds"
    flipped = "drops" if current == "holds" else "holds"
    text = base.text
    pairs = _REVERSALS if current == "holds" else tuple((b, a) for a, b in _REVERSALS)
    for old, new in pairs:
        if old in text:
            text = text.replace(old, new, 1)
            break
    else:
        text = f"{text} The pooled observed value {'drops below' if flipped == 'drops' else 'holds at or above'} the threshold."
    return base.model_copy(update={"direction": flipped, "text": text})


def _wrong_section_count(base: Claim, finding: AuditResult, _: Any) -> Claim:
    actual = len(finding.eligible_section_ids)
    wrong = actual - 3 if actual > 3 else actual + 2
    cited = dict(base.cited)
    name = next((n for n, c in cited.items() if c.source.strip() == "eligible_section_ids.count"), "eligible_section_ids.count")
    cited[name] = CitedNumber(value=wrong, source="eligible_section_ids.count")
    text, count = re.subn(rf"(?<![\d.]){actual}(?![\d.]|\s*%)", str(wrong), base.text, count=1)
    if not count:
        text = f"{base.text} Pooled over {wrong} eligible sections."
    return base.model_copy(update={"cited": cited, "text": text})


def _wrong_dataset_reference(base: Claim, finding: AuditResult, _: Any) -> Claim:
    return base.model_copy(update={"dataset_id": WRONG_DATASET, "text": base.text.replace(base.dataset_id, WRONG_DATASET)})


def _changed_effect(base: Claim, finding: AuditResult, _: Any) -> Claim:
    floats = [(n, c) for n, c in base.cited.items() if isinstance(c.value, float)]
    preferred = [(n, c) for n, c in floats if "observed_value" in c.source and "[default]" not in c.source]
    name, number = (preferred or floats or [(None, None)])[0]
    if number is None:
        name, number = next(iter(base.cited.items()))
    old = float(number.value or 0.0)
    new = old + EFFECT_SHIFT if old + EFFECT_SHIFT <= 1.0 else old - EFFECT_SHIFT
    cited = {**base.cited, name: CitedNumber(value=new, source=number.source)}
    return base.model_copy(update={"cited": cited, "text": _rewrite_number(base.text, old, new)})


def _figure_label_mismatch(base: Claim, finding: AuditResult, other_figure_id: str | None) -> Claim:
    return base.model_copy(update={"figure_id": other_figure_id or "fig-0000000000000000"})


def _misstated_spatial_pattern(base: Claim, finding: AuditResult, _: Any) -> Claim:
    if base.neighbour_pattern is not None:
        current = base.neighbour_pattern
    else:
        current = _computed_pattern(finding) or "excluded_not_nearer_home"
    flipped = "excluded_not_nearer_home" if current == "excluded_nearer_home" else "excluded_nearer_home"
    text = base.text
    swaps = (("more often than", "no more often than"),) if current == "excluded_nearer_home" else (("no more often than", "more often than"),)
    for old, new in swaps:
        if old in text:
            text = text.replace(old, new, 1)
            break
    else:
        nearer = "more often" if flipped == "excluded_nearer_home" else "no more often"
        text = f"{text} Excluded molecules lie closer to a cell of their gene's home type {nearer} than retained molecules do."
    return base.model_copy(update={"neighbour_pattern": flipped, "text": text})


def _missing_required_control(base: Claim, finding: AuditResult, _: Any) -> Claim:
    controls = base.controls
    if controls.label_sensitivity is not None:
        dropped = ClaimControls(random_thinning=controls.random_thinning, label_sensitivity=None)
    else:
        dropped = ClaimControls(random_thinning=None, label_sensitivity=None)
    return base.model_copy(update={"controls": dropped})


def _computed_pattern(finding: AuditResult) -> str | None:
    where = evidence_section(finding)
    section = next((s for s in finding.sections if where and s.section_id == where[0]), None)
    row = next((c for c in (section.conditions if section else []) if where and c.condition.value == where[1]), None)
    return pattern_of(row.neighbour_proximity_share_excluded, row.neighbour_proximity_share_retained) if row else None


def _rewrite_number(text: str, old: float, new: float) -> str:
    """Replace the text's writing of `old` (as a percentage or a fraction, at the precision written) with `new`."""
    for match in re.finditer(r"(?<![\w.])(\d+(?:\.\d+)?)(\s*%)?", text):
        written, percent = match.group(1), bool(match.group(2))
        decimals = len(written.split(".")[1]) if "." in written else 0
        for scale in ((100.0,) if percent else (1.0, 100.0)):
            if abs(float(written) - old * scale) <= 0.5 * 10**-decimals + 1e-9:
                replacement = f"{new * scale:.{decimals}f}"
                return text[: match.start(1)] + replacement + text[match.end(1):]
    return text


_INJECTORS: dict[InjectedErrorKind, Callable[[Claim, AuditResult, Any], Claim]] = {
    InjectedErrorKind.REVERSED_DIRECTION: _reversed_direction,
    InjectedErrorKind.WRONG_SECTION_COUNT: _wrong_section_count,
    InjectedErrorKind.WRONG_DATASET_REFERENCE: _wrong_dataset_reference,
    InjectedErrorKind.CHANGED_EFFECT: _changed_effect,
    InjectedErrorKind.FIGURE_LABEL_MISMATCH: _figure_label_mismatch,
    InjectedErrorKind.MISSTATED_SPATIAL_PATTERN: _misstated_spatial_pattern,
    InjectedErrorKind.MISSING_REQUIRED_CONTROL: _missing_required_control,
}
