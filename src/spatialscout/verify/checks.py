"""The structural and numerical checks on one claim, and the required-controls policy.

Structural (spec "Verification scope"): schema validity; the dataset, finding, figure and control references
resolve; section counts match; required controls are present and belong to the claim's finding:

- a home-matched random-thinning control for any claim about assignment sensitivity (every audit claim);
- a label-sensitivity check for any claim about a population whose label rule involves the claim's genes, or
  decides membership against those genes' home cell type.

Numerical: every cited number, the stated direction and the stated neighbour pattern against the independent
recompute (`recompute.py`), within its declared tolerances.
"""

import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel, ValidationError

from ..contracts import (
    CLAIM_SCHEMA_VERSION,
    AuditResult,
    CheckResult,
    Claim,
    CompositeFigure,
    LabelRule,
    LabelRuleSet,
    LabelSensitivityCheck,
    RandomThinningControl,
)
from .citations import UnresolvedSource, resolve_source, split_source
from .recompute import HOME_OF, TOLERANCES, Node

MISSING_CONTROL = "required control not run"


# --- required controls -------------------------------------------------------------------------------------------


def claim_genes(finding: AuditResult) -> list[str]:
    """The genes a claim about this finding is about: for the co-expression score, the scored foreign markers."""
    if finding.measure == "co_expression_score":
        return [g for g in finding.genes if HOME_OF.get(g) != finding.population.cell_type]
    return list(finding.genes)


def required_controls(finding: AuditResult, label_rules: LabelRuleSet | Sequence[LabelRule] | None) -> dict[str, str]:
    """Each control a claim about this finding must cite, with the rule that requires it. `label_rules`: the
    dataset's frozen rules (a rule set or a list of rules); None when its labels are given by construction."""
    required = {"random_thinning": "a claim about assignment sensitivity must cite a home-matched random-thinning control"}
    cell_type, rule_id = finding.population.cell_type, finding.population.label_rule_id
    genes = claim_genes(finding)
    rules = label_rules.rules if isinstance(label_rules, LabelRuleSet) else (label_rules or [])
    rule = next((r for r in rules if r.label_rule_id == rule_id), None)
    if rule is not None:
        markers = {g for marker_genes in rule.markers.values() for g in marker_genes}
        involved = [g for g in genes if g in markers or g in rule.ignored_genes]
        competing = [g for g in genes if HOME_OF.get(g) not in (None, cell_type) and HOME_OF[g] in rule.markers]
    else:
        # A rule recorded without its markers (labels given by construction): any marker gene may decide membership.
        involved, competing = [g for g in genes if g in HOME_OF], []
    if involved or competing:
        reasons = []
        if involved:
            reasons.append(f"{rule_id} reads {', '.join(sorted(set(involved)))}")
        if competing:
            homes = sorted({HOME_OF[g] for g in competing})
            reasons.append(f"{rule_id} decides {cell_type} membership against {', '.join(homes)}, the home type of "
                           f"{', '.join(sorted(set(competing)))}")
        required["label_sensitivity"] = "a claim about this population must cite a label-sensitivity check: " + "; ".join(reasons)
    return required


# --- structural ----------------------------------------------------------------------------------------------------


def structural_check(
    claim: Claim,
    finding: AuditResult | None,
    controls: Mapping[str, BaseModel],
    figures: Mapping[str, CompositeFigure],
    datasets: Sequence[str],
    label_rules: LabelRuleSet | None,
) -> CheckResult:
    reasons: list[str] = []
    try:
        Claim.model_validate(claim.model_dump(mode="json"))
    except ValidationError as error:
        reasons.append(f"the claim does not match the claim schema ({error.error_count()} errors)")
    if claim.schema_version != CLAIM_SCHEMA_VERSION:
        reasons.append(f"claim schema {claim.schema_version}, expected {CLAIM_SCHEMA_VERSION}")
    if claim.dataset_id not in datasets:
        reasons.append(f"dataset reference {claim.dataset_id!r} names no dataset served here")
    if finding is None or finding.finding_id != claim.finding.finding_id:
        reasons.append(f"finding reference {claim.finding.finding_id!r} resolves to no finding of this investigation")
        return _result("structural", reasons)
    if claim.dataset_id != finding.dataset_id:
        reasons.append(f"dataset reference {claim.dataset_id!r} does not match the finding's dataset {finding.dataset_id!r}")
    if claim.finding.finding_kind != finding.finding_kind:
        reasons.append(f"finding kind {claim.finding.finding_kind!r} does not match the finding's {finding.finding_kind!r}")

    cited_controls = {cid: controls[cid] for cid in (claim.controls.random_thinning, claim.controls.label_sensitivity) if cid in controls}
    for name, number in claim.cited.items():
        try:
            actual = resolve_source(number.source, finding, cited_controls)
        except UnresolvedSource as error:
            reasons.append(f"cited {name}: {error}")
            continue
        if _is_section_count(number.source) and actual != number.value:
            reasons.append(f"section count mismatch: the claim cites {number.value} for {number.source}, the finding has {actual}")

    reasons += _control_problems(claim, finding, controls, label_rules)
    if claim.figure_id is not None:
        figure = figures.get(claim.figure_id)
        if figure is None:
            reasons.append(f"figure reference {claim.figure_id!r} resolves to no figure")
        elif figure.finding_id != finding.finding_id:
            reasons.append(f"figure-label mismatch: figure {claim.figure_id} shows finding {figure.finding_id}, not {finding.finding_id}")
    return _result("structural", reasons)


def _is_section_count(source: str) -> bool:
    segments = split_source(source)
    return segments[-1] == "count" and segments[-2] in ("eligible_section_ids", "sections")


def _control_problems(claim: Claim, finding: AuditResult, controls: Mapping[str, BaseModel], label_rules: LabelRuleSet | None) -> list[str]:
    problems = []
    required = required_controls(finding, label_rules)
    thinning_id, label_id = claim.controls.random_thinning, claim.controls.label_sensitivity
    if "random_thinning" in required:
        control = controls.get(thinning_id) if thinning_id else None
        if thinning_id is None:
            problems.append(f"{MISSING_CONTROL}: random-thinning control ({required['random_thinning']})")
        elif not isinstance(control, RandomThinningControl):
            problems.append(f"random-thinning control {thinning_id} resolves to no random-thinning control")
        elif control.finding_id != finding.finding_id:
            problems.append(f"random-thinning control {thinning_id} is about finding {control.finding_id}, not {finding.finding_id}")
        elif not any(p.expectation_home_matched is not None for p in control.pooled) and not any(
            c.expectation_home_matched is not None for section in control.sections for c in section.conditions
        ):
            problems.append(f"random-thinning control {thinning_id} has no home-matched expectation")
    if "label_sensitivity" in required:
        check = controls.get(label_id) if label_id else None
        if label_id is None:
            problems.append(f"{MISSING_CONTROL}: label-sensitivity check ({required['label_sensitivity']})")
        elif not isinstance(check, LabelSensitivityCheck):
            problems.append(f"label-sensitivity check {label_id} resolves to no label-sensitivity check")
        elif not any(arm.finding_id == finding.finding_id for arm in check.arms):
            problems.append(f"label-sensitivity check {label_id} has no arm on finding {finding.finding_id}")
    return problems


# --- numerical -----------------------------------------------------------------------------------------------------

_HOLDS = re.compile(r"\b(persist\w*|remain\w*|stay\w*|holds?|held|at or above|retain\w*|survive\w*|unchanged)\b")
_DROPS = re.compile(r"\b(falls?|fell|falling|drops?|dropped|dropping|declines?|declined|vanish\w*|lost|loses?)\b[^.;]{0,30}\bbelow\b"
                    r"|\b(falls?|fell|drops?|dropped)\b|\bbelow the (home-matched )?(expectation|threshold)")
_NEGATED_DROP = re.compile(r"\b(no|not|never|without|none)\b[^.;]{0,40}?\b(fall\w*|fell|drop\w*|below)\b")


def stated_direction(claim: Claim) -> str | None:
    """The direction a claim states: its structured field, else read from its text (a negated drop, such as "no
    condition dropping below", reads as holds)."""
    if claim.direction is not None:
        return claim.direction
    text = _NEGATED_DROP.sub(" ", claim.text.lower())
    if _DROPS.search(text):
        return "drops"
    if _HOLDS.search(text):
        return "holds"
    return None


def evidence_section(finding: AuditResult) -> tuple[str, str] | None:
    """Panel B's section and condition: the top-ranked evidence region's."""
    region = next((r for r in finding.evidence_regions if r.rank == 1), None)
    if region is None or region.condition is None:
        return None
    return region.region.section_id, region.condition.value


def pattern_of(excluded: float | None, retained: float | None) -> str | None:
    if excluded is None or retained is None:
        return None
    return "excluded_nearer_home" if excluded > retained else "excluded_not_nearer_home"


def numerical_check(
    claim: Claim,
    finding: AuditResult | None,
    controls: Mapping[str, BaseModel],
    recomputed: Node | None,
    recomputed_arms: Mapping[str, Node] | None = None,
    unavailable_reason: str | None = None,
) -> tuple[CheckResult, dict[str, Any]]:
    """Every cited number against the recompute, then the stated direction and neighbour pattern. A number the
    recompute does not cover leaves the check unavailable, never passed."""
    if finding is None or recomputed is None:
        reason = unavailable_reason or "the cited finding did not resolve, so nothing could be recomputed"
        return CheckResult(kind="numerical", status="unavailable", details=reason, reasons=[reason]), {}
    failures, uncovered, values = [], [], {}
    for name, number in claim.cited.items():
        try:
            actual = _recomputed_value(number.source, claim, controls, recomputed, recomputed_arms or {})
        except (UnresolvedSource, KeyError, AttributeError, IndexError, TypeError):
            uncovered.append(f"cited {name} ({number.source}) is not covered by the independent recompute")
            continue
        values[number.source] = actual
        if not _within(number.value, actual):
            failures.append(f"cited {name} is {number.value}, but the independent recompute of {number.source} gives {_fmt(actual)}")
    stated = stated_direction(claim)
    if stated is not None and recomputed.direction is not None and stated != recomputed.direction:
        failures.append(f"the claim states the observed value {_direction_text(stated)}, but recomputed it {_direction_text(recomputed.direction)}")
    values["direction"] = recomputed.direction
    if claim.neighbour_pattern is not None:
        where = evidence_section(finding)
        section = next((s for s in recomputed.sections if where and s.section_id == where[0]), None)
        row = next((c for c in (section.conditions if section else []) if where and c.condition == where[1]), None)
        actual_pattern = pattern_of(row.neighbour_proximity_share_excluded, row.neighbour_proximity_share_retained) if row else None
        values["neighbour_pattern"] = actual_pattern
        if actual_pattern is None:
            uncovered.append("the stated neighbour pattern has no recomputed neighbour-proximity shares to check against")
        elif actual_pattern != claim.neighbour_pattern:
            failures.append(
                f"misstated spatial pattern: the claim states {claim.neighbour_pattern.replace('_', ' ')}, but the recomputed "
                f"neighbour-proximity shares in {where[0]} under {where[1]} are {_fmt(row.neighbour_proximity_share_excluded)} "
                f"(excluded) and {_fmt(row.neighbour_proximity_share_retained)} (retained)"
            )
    if failures:
        return CheckResult(kind="numerical", status="failed", details=failures[0], reasons=failures + uncovered), values
    if uncovered:
        return CheckResult(kind="numerical", status="unavailable", details=uncovered[0], reasons=uncovered), values
    return CheckResult(kind="numerical", status="passed", details=f"{len(claim.cited)} cited numbers match the independent recompute"), values


def _recomputed_value(source: str, claim: Claim, controls: Mapping[str, BaseModel], recomputed: Node, arms: Mapping[str, Node]) -> Any:
    segments = split_source(source.strip())
    if segments[0].startswith("controls["):
        control = controls[segments[0][len("controls["):-1]]
        rest = segments[1:]
        if isinstance(control, RandomThinningControl):
            return resolve_source(".".join(rest), recomputed)  # the control's values are its finding's
        if isinstance(control, LabelSensitivityCheck) and rest and rest[0].startswith("arms["):
            arm = arms[rest[0][len("arms["):-1]]
            tail = rest[1:]
            if tail == ["cells_labelled"]:
                return sum(s.cells_labelled for s in arm.sections)
            return resolve_source(".".join(tail), arm)
        raise KeyError(source)
    return resolve_source(source, recomputed)


def _within(cited: float | int | None, actual: Any) -> bool:
    if cited is None or actual is None:
        return cited is None and actual is None
    if isinstance(cited, float) and not math.isfinite(cited):
        return False
    if isinstance(actual, int) and isinstance(cited, int):
        return abs(cited - actual) <= TOLERANCES["count_abs"]
    text = repr(float(cited))
    decimals = len(text.split(".")[1]) if "." in text and "e" not in text else 0
    written = 0.5 * 10**-decimals if decimals < 12 else 0.0
    return abs(float(cited) - float(actual)) <= max(written, TOLERANCES["fraction_abs"])


def _direction_text(direction: str) -> str:
    return "holds at or above the home-matched threshold" if direction == "holds" else "drops below the home-matched threshold"


def _fmt(value: Any) -> str:
    return f"{value:.4g}" if isinstance(value, float) else str(value)


def _result(kind: str, reasons: list[str]) -> CheckResult:
    if reasons:
        return CheckResult(kind=kind, status="failed", details=reasons[0], reasons=reasons)
    return CheckResult(kind=kind, status="passed", details="references, section counts and required controls check out")
