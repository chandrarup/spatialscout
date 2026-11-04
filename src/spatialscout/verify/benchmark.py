"""The verification benchmark: valid claims derived from the committed GSE286184 audit results, and every injected
error kind derived from each, verified exactly as an investigation verifies its claims.

    uv run spatialscout benchmark                    # or `make benchmark`: replays the stored visual checks offline
    uv run spatialscout benchmark --run-mode live    # Muse Spark 1.3 reads every figure again and is re-recorded

- One valid claim per committed audit result, worded from its computed values: its direction (from the pooled values
  against the frozen threshold), its neighbour pattern in Panel B's section (from the computed shares), and the
  required controls the batch computed. Nothing is chosen to make the verifier look good.
- Held-out subset: every third result in index order. The verifier's prompt and tolerances were written before the
  benchmark was first run and were not changed after reading the held-out results; rates are reported on all claims,
  the development subset and the held-out subset.
- Detection: an injected claim counts as detected by a check when that check finds a problem the valid claim it was
  derived from did not have. False rejection: a valid claim that a check fails or disputes.

Visual checks are stored in `fixtures/benchmark/recording.json`; results go to `artifacts/GSE286184/benchmark/`.
The numerical check reads the ingested molecule tables (`make data`); without them it is reported unavailable.
"""

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from ..contracts import (
    AuditIndex,
    AuditResult,
    CitedNumber,
    Claim,
    ClaimControls,
    FindingRef,
    InjectedErrorKind,
    LabelSensitivityCheck,
    RandomThinningControl,
    ReplayInfo,
)
from ..data import DatasetStore
from ..gateway import ModelGateway
from .checks import evidence_section, pattern_of
from .recompute import THRESHOLD
from .verifier import VerificationContext, challenge, reasons_of, verify_claim

DATASET = "GSE286184"
RECORDING_ID = "benchmark-gse286184-visual"
CHECKS = ("structural", "numerical", "visual")
MEASURE_TEXT = {
    "share_expressing": "share of cells expressing {genes}",
    "gene_set_share_expressing": "share of cells expressing {genes}",
    "co_expression_score": "co-expression score of exclusive marker pairs",
}


def recording_info() -> ReplayInfo:
    return ReplayInfo(
        recording_id=RECORDING_ID,
        recorded_at=datetime.now(UTC),
        origin="live",
        question="verification benchmark: visual checks of the GSE286184 composite figures",
        note="Muse Spark 1.3 visual checks recorded live by `spatialscout benchmark --run-mode live`; nothing was retried or edited.",
        dataset_id=DATASET,
    )


def valid_claim(slug: str, finding: AuditResult, thinning: RandomThinningControl, labels: LabelSensitivityCheck | None) -> Claim:
    """The valid claim about one audit result, worded and cited from its computed values only."""
    pooled = {p.condition.value: p for p in finding.pooled}
    default, strict = pooled["default"], pooled["nucleus_only"]
    stricter = [p for p in finding.pooled if p.condition.value != "default"]
    direction = "drops" if any(p.observed_value < p.expectation_home_matched * THRESHOLD for p in stricter) else "holds"
    measure = MEASURE_TEXT[finding.measure].format(genes=" or ".join(finding.genes))
    verb = "stays at or above" if direction == "holds" else "falls below"
    n = len(finding.eligible_section_ids)
    text = (
        f"In cells labelled {finding.population.cell_type} by our {finding.population.label_rule_id} rule in {finding.dataset_id}, "
        f"the {measure} {verb} the home-matched expectation x 2^-0.5 under the tested stricter conditions: pooled over {n} "
        f"eligible sections it is {default.observed_value:.1%} under the default condition and {strict.observed_value:.1%} "
        f"under nucleus-only, against a home-matched expectation of {strict.expectation_home_matched:.1%}."
    )
    cited = {
        "eligible_sections": CitedNumber(value=n, source="eligible_section_ids.count"),
        "observed_default": CitedNumber(value=default.observed_value, source="pooled[default].observed_value"),
        "observed_nucleus_only": CitedNumber(value=strict.observed_value, source="pooled[nucleus_only].observed_value"),
        "home_matched_nucleus_only": CitedNumber(value=strict.expectation_home_matched, source="pooled[nucleus_only].expectation_home_matched"),
    }
    pattern = None
    where = evidence_section(finding)
    if where is not None:
        section = next(s for s in finding.sections if s.section_id == where[0])
        row = next(c for c in section.conditions if c.condition.value == where[1])
        pattern = pattern_of(row.neighbour_proximity_share_excluded, row.neighbour_proximity_share_retained)
        if pattern is not None:
            base = f"sections[{where[0]}].conditions[{where[1]}]"
            cited["near_home_excluded"] = CitedNumber(value=row.neighbour_proximity_share_excluded, source=f"{base}.neighbour_proximity_share_excluded")
            cited["near_home_retained"] = CitedNumber(value=row.neighbour_proximity_share_retained, source=f"{base}.neighbour_proximity_share_retained")
            often = "more often than" if pattern == "excluded_nearer_home" else "no more often than"
            text += (
                f" In {where[0]}, molecules excluded under {where[1].replace('_', '-')} lie closer to a cell of their gene's home "
                f"type {often} retained ones ({row.neighbour_proximity_share_excluded:.0%} vs {row.neighbour_proximity_share_retained:.0%})."
            )
    return Claim(
        claim_id=f"bench-{slug}",
        investigation_id="benchmark",
        dataset_id=finding.dataset_id,
        finding=FindingRef(finding_id=finding.finding_id, finding_kind="audit"),
        text=text,
        cited=cited,
        controls=ClaimControls(random_thinning=thinning.control_id, label_sensitivity=labels.control_id if labels else None),
        evidence_status=finding.label,
        direction=direction,
        neighbour_pattern=pattern,
    )


def load_world(artifacts_dir: Path) -> tuple[AuditIndex, dict[str, AuditResult], dict[str, BaseModel], dict[str, Any], dict[str, bytes]]:
    root = artifacts_dir / DATASET
    index = AuditIndex.model_validate_json((root / "audit" / "index.json").read_text(encoding="utf-8"))
    findings, controls, figures, pngs = {}, {}, {}, {}
    for entry in index.entries:
        findings[entry.finding_id] = AuditResult.model_validate_json((root / entry.finding_path).read_text(encoding="utf-8"))
        if entry.random_thinning_control_path:
            control = RandomThinningControl.model_validate_json((root / entry.random_thinning_control_path).read_text(encoding="utf-8"))
            controls[control.control_id] = control
        if entry.label_sensitivity_control_path:
            check = LabelSensitivityCheck.model_validate_json((root / entry.label_sensitivity_control_path).read_text(encoding="utf-8"))
            controls[check.control_id] = check
        if entry.figure is not None:
            figures[entry.figure.figure_id] = entry.figure
            pngs[entry.figure.figure_id] = (root / entry.figure.path).read_bytes()
    return index, findings, controls, figures, pngs


async def run_benchmark(store: DatasetStore, artifacts_dir: Path, gateway: ModelGateway | None, log: Callable[[str], None] = print) -> dict[str, Any]:
    index, findings, controls, figures, pngs = load_world(artifacts_dir)
    context = VerificationContext(
        datasets=store.dataset_ids(),
        findings=findings,
        controls=controls,
        figures=figures,
        figure_png=pngs,
        label_rules=store.label_rules(DATASET),
        load_sections=lambda ids, rule: [store.load_section(i, rule) for i in ids],
        gateway=gateway,
    )
    rows: list[dict[str, Any]] = []
    entries = index.entries
    for position, entry in enumerate(entries):
        split = "held_out" if position % 3 == 2 else "development"
        finding = findings[entry.finding_id]
        claim = valid_claim(entry.slug, finding, controls[entry.random_thinning_control_id],
                            controls.get(entry.label_sensitivity_control_id or ""))
        verified, verification = await verify_claim(claim, context)
        statuses = {c.kind: c.status for c in verification.checks}
        rows.append({"claim_id": claim.claim_id, "slug": entry.slug, "split": split, "injected": None,
                     "verification_status": verification.verification_status.value, "checks": statuses,
                     "reasons": reasons_of(verification), "text": claim.text})
        other = entries[(position + 1) % len(entries)].figure
        challenges = await challenge(verified, verification, context, other_figure_id=other.figure_id if other else None)
        for variant in challenges.variants:
            v_statuses = {c.kind: c.status for c in variant.verification.checks}
            caught_by = [c.kind for c in variant.verification.checks
                         if c.status in ("failed", "disputed") and any(r in variant.new_reasons for r in c.reasons)]
            rows.append({"claim_id": variant.claim.claim_id, "slug": entry.slug, "split": split, "injected": variant.kind.value,
                         "verification_status": variant.verification.verification_status.value, "checks": v_statuses,
                         "detected": variant.detected, "caught_by": caught_by, "new_reasons": variant.new_reasons,
                         "changes": [c.model_dump(mode="json") for c in variant.changes]})
        log(f"{entry.slug} ({split}): valid claim {verification.verification_status.value}; "
            + ", ".join(f"{v.kind.value} {'caught' if v.detected else 'missed'}" for v in challenges.variants))
    return {"dataset_id": DATASET, "recording_id": RECORDING_ID, "summary": summarise(rows), "claims": rows}


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for subset in ("all", "development", "held_out"):
        chosen = [r for r in rows if subset == "all" or r["split"] == subset]
        valid = [r for r in chosen if r["injected"] is None]
        injected = [r for r in chosen if r["injected"] is not None]
        by_kind = {}
        for kind in InjectedErrorKind:
            of_kind = [r for r in injected if r["injected"] == kind.value]
            if not of_kind:
                continue
            by_kind[kind.value] = {
                "claims": len(of_kind),
                "detected": _rate(sum(r["detected"] for r in of_kind), len(of_kind)),
                "by_check": {check: _rate(sum(check in r["caught_by"] for r in of_kind), len(of_kind)) for check in CHECKS},
                "visual_unavailable": sum(r["checks"].get("visual") == "unavailable" for r in of_kind),
            }
        out[subset] = {
            "valid_claims": len(valid),
            "injected_claims": len(injected),
            "valid_status": {s: sum(r["verification_status"] == s for r in valid) for s in ("verified", "disputed", "failed", "unavailable")},
            "false_rejection": {
                "any_check": _rate(sum(r["verification_status"] in ("failed", "disputed") for r in valid), len(valid)),
                **{check: _rate(sum(r["checks"].get(check) in ("failed", "disputed") for r in valid), len(valid)) for check in CHECKS},
            },
            "detection": {
                "any_check": _rate(sum(r["detected"] for r in injected), len(injected)),
                "by_kind": by_kind,
            },
        }
    return out


def _rate(numerator: int, denominator: int) -> dict[str, Any]:
    return {"count": numerator, "of": denominator, "rate": round(numerator / denominator, 4) if denominator else None}


def write_results(results: dict[str, Any], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "results.json"
    path.write_text(json.dumps(results, indent=1, allow_nan=False) + "\n", encoding="utf-8")
    return path
